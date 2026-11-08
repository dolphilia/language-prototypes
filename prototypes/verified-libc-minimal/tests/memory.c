#include "vp_memory.h"
#include <limits.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <unistd.h>

typedef void *(*copy_fn)(void *, const void *, size_t);
extern int vp_check_copy_abi(copy_fn, void *, const void *, size_t);
extern int vp_check_fill_abi(void *(*)(void *, int, size_t), void *, int, size_t);
static size_t checks;
#define CHECK(x) do { ++checks; if (!(x)) { \
  fprintf(stderr,"check failed at %s:%d: %s\n",__FILE__,__LINE__,#x); exit(1); \
} } while (0)
static uint32_t seed = 0x19273645;
static uint32_t random_word(void) {
  seed ^= seed << 13; seed ^= seed >> 17; seed ^= seed << 5; return seed;
}
static void data(unsigned char *p, size_t n) {
  for (size_t i=0; i<n; ++i) p[i]=(unsigned char)random_word();
}
static void copy_case(copy_fn fn,size_t n,size_t sa,size_t da) {
  unsigned char src[800],before[800],dst[800],ref[800],libc_ref[800];
  data(src,sizeof(src)); data(dst,sizeof(dst));
  for (size_t i=0;i<sizeof(src);++i) before[i]=src[i];
  for (size_t i=0;i<sizeof(dst);++i) ref[i]=libc_ref[i]=dst[i];
  unsigned char *s=src+32+sa,*d=dst+32+da;
  for (size_t i=0;i<n;++i) ref[32+da+i]=s[i];
  CHECK(memcpy(libc_ref+32+da,s,n)==libc_ref+32+da);
  CHECK(fn(d,s,n)==d);
  CHECK(memcmp(src,before,sizeof(src))==0);
  CHECK(memcmp(dst,ref,sizeof(dst))==0);
  CHECK(memcmp(dst,libc_ref,sizeof(dst))==0);
}
static void fill_case(size_t n,size_t da,int c) {
  unsigned char dst[800],ref[800],libc_ref[800];
  data(dst,sizeof(dst));
  for (size_t i=0;i<sizeof(dst);++i) ref[i]=libc_ref[i]=dst[i];
  for (size_t i=0;i<n;++i) ref[32+da+i]=(unsigned char)c;
  CHECK(memset(libc_ref+32+da,c,n)==libc_ref+32+da);
  CHECK(vp_memset(dst+32+da,c,n)==dst+32+da);
  CHECK(memcmp(dst,ref,sizeof(dst))==0);
  CHECK(memcmp(dst,libc_ref,sizeof(dst))==0);
}
struct guarded { unsigned char *mapping,*page; size_t length; };
static struct guarded guarded(void) {
  long p=sysconf(_SC_PAGESIZE); CHECK(p>0);
  void *m=mmap(NULL,(size_t)p*3,PROT_NONE,MAP_ANON|MAP_PRIVATE,-1,0);
  CHECK(m!=MAP_FAILED);
  CHECK(mprotect((unsigned char*)m+p,(size_t)p,PROT_READ|PROT_WRITE)==0);
  return (struct guarded){m,(unsigned char*)m+p,(size_t)p};
}
static void guards(copy_fn fn,size_t n) {
  struct guarded src=guarded(),dst=guarded();
  /* Both ends, including an inaccessible non-NULL pointer for zero length. */
  for (unsigned edge=0;edge<2;++edge) {
    unsigned char *s=src.page+(edge?src.length-n:0);
    unsigned char *d=dst.page+(edge?dst.length-n:0);
    data(src.page,src.length); data(dst.page,dst.length);
    CHECK(mprotect(src.page,src.length,PROT_READ)==0);
    CHECK(fn(d,s,n)==d);
    for (size_t i=0;i<n;++i) CHECK(d[i]==s[i]);
    CHECK(vp_memset(d,-1,n)==d);
    for (size_t i=0;i<n;++i) CHECK(d[i]==255);
    CHECK(mprotect(src.page,src.length,PROT_READ|PROT_WRITE)==0);
  }
  CHECK(munmap(src.mapping,src.length*3)==0);
  CHECK(munmap(dst.mapping,dst.length*3)==0);
}
int main(void) {
  static const size_t lengths[]={0,1,2,7,8,9,15,16,17,31,32,63,64,255,256};
  static const int values[]={0,1,255,256,-1,INT_MIN,INT_MAX,-257};
  copy_fn functions[]={vp_memcpy_scalar,vp_memcpy};
  for (size_t f=0;f<2;++f)
    for (size_t l=0;l<sizeof(lengths)/sizeof(*lengths);++l) {
      size_t n=lengths[l];
      for (size_t sa=0;sa<16;++sa) for (size_t da=0;da<16;++da)
        copy_case(functions[f],n,sa,da);
      guards(functions[f],n);
    }
  for (size_t l=0;l<sizeof(lengths)/sizeof(*lengths);++l)
    for (size_t da=0;da<16;++da)
      for (size_t c=0;c<sizeof(values)/sizeof(*values);++c)
        fill_case(lengths[l],da,values[c]);
  for (size_t i=0;i<2000;++i) {
    size_t n=random_word()%513,sa=random_word()%16,da=random_word()%16;
    copy_case(functions[i%2],n,sa,da); fill_case(n,da,(int)random_word());
  }
  _Alignas(16) unsigned char src[64],dst[64]; data(src,sizeof(src));
  for (size_t f=0;f<2;++f) for (size_t n=0;n<=32;++n)
    CHECK(vp_check_copy_abi(functions[f],dst,src,n)==0);
  for (size_t n=0;n<=32;++n) CHECK(vp_check_fill_abi(vp_memset,dst,-257,n)==0);
  printf("native: %zu checks passed (seed 0x19273645, bounds/guards/ABI)\n",checks);
  return 0;
}
