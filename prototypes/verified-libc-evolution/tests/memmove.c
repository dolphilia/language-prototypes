#include "vp2_evolution.h"
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <unistd.h>
typedef void *(*move_fn)(void *,const void *,size_t);
extern int vp2_check_copy_abi(move_fn,void *,const void *,size_t);
static move_fn volatile external_move=memmove;
static size_t checks;
static uint32_t seed=0x19273645;
#define CHECK(p) do { ++checks; if (!(p)) { fprintf(stderr,"memmove failure line %d: %s\n",__LINE__,#p);exit(1); } } while(0)
static uint32_t random_word(void) { seed^=seed<<13;seed^=seed>>17;seed^=seed<<5;return seed; }
static void overlap(size_t n,ptrdiff_t delta,size_t offset) {
  size_t extent=3*n+256,source=n+64+offset;
  size_t destination=(size_t)((ptrdiff_t)source+delta);
  unsigned char *arena=malloc(extent),*before=malloc(extent),*expected=malloc(extent),*libc=malloc(extent);
  CHECK(arena && before && expected && libc);
  CHECK(source+n<=extent && destination+n<=extent);
  for(size_t i=0;i<extent;++i) before[i]=arena[i]=expected[i]=libc[i]=(unsigned char)random_word();
  for(size_t i=0;i<n;++i) expected[destination+i]=before[source+i];
  CHECK(external_move(libc+destination,libc+source,n)==libc+destination);
  CHECK(vp2_memmove(arena+destination,arena+source,n)==arena+destination);
  CHECK(memcmp(arena,expected,extent)==0);
  CHECK(memcmp(arena,libc,extent)==0);
  for(size_t i=0;i<extent;++i) arena[i]=before[i];
  CHECK(vp2_check_copy_abi(vp2_memmove,arena+destination,arena+source,n)==0);
  CHECK(memcmp(arena,expected,extent)==0);
  free(arena);free(before);free(expected);free(libc);
}
static void guards(size_t n) {
  long page_size=sysconf(_SC_PAGESIZE);CHECK(page_size>1);
  size_t p=(size_t)page_size;CHECK(p>n);
  unsigned char *mapping=mmap(NULL,3*p,PROT_NONE,MAP_PRIVATE|MAP_ANON,-1,0);
  CHECK(mapping!=MAP_FAILED);
  unsigned char *page=mapping+p;
  CHECK(mprotect(page,p,PROT_READ|PROT_WRITE)==0);
  unsigned char *before=malloc(p),*expected=malloc(p);CHECK(before && expected);
  for(unsigned placement=0;placement<4;++placement) {
    size_t source=placement==0?0:placement==1?1:placement==2?p-n:p-n-1;
    size_t destination=placement==0?1:placement==1?0:placement==2?source-1:source+1;
    for(size_t i=0;i<p;++i) page[i]=before[i]=expected[i]=(unsigned char)random_word();
    for(size_t i=0;i<n;++i) expected[destination+i]=before[source+i];
    CHECK(vp2_memmove(page+destination,page+source,n)==page+destination);
    CHECK(memcmp(page,expected,p)==0);
  }
  /* Empty ranges need no data mapping; both pointers remain non-NULL. */
  CHECK(vp2_memmove(mapping,mapping,0)==mapping);
  CHECK(munmap(mapping,3*p)==0);free(before);free(expected);
}
int main(void) {
  const size_t lengths[]={0,1,2,3,4,7,8,9,15,16,17,31,32,33,63,64,65,255,256,257,1024,4095,4096,4097};
  for(size_t k=0;k<sizeof(lengths)/sizeof(*lengths);++k) {
    size_t n=lengths[k];ptrdiff_t v=(ptrdiff_t)n,less=n?v-1:0;
    ptrdiff_t shifts[]={0,1,-1,less,-less,v,-v,v+1,-v-1};
    for(size_t alignment=0;alignment<16;++alignment)
      for(size_t d=0;d<sizeof(shifts)/sizeof(*shifts);++d) overlap(n,shifts[d],alignment);
  }
  for(size_t i=0;i<1000;++i) {
    size_t n=random_word()%4097;ptrdiff_t distance=(ptrdiff_t)(random_word()%(2*n+3))-(ptrdiff_t)n-1;
    overlap(n,distance,random_word()%16);
  }
  long page_size=sysconf(_SC_PAGESIZE);CHECK(page_size>1);
  size_t page=(size_t)page_size;
  guards(1);guards(8);guards(31);guards(page-1);
  printf("native memmove: %zu checks passed (snapshot/libc/overlap/guards/ABI, seed 0x19273645)\n",checks);
  return 0;
}
