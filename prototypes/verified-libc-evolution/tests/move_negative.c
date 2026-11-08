#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <sys/mman.h>
#include <unistd.h>
extern void *vp2_memmove(void *,const void *,size_t);

int main(int argc,char **argv) {
  if(argc!=2)return 2;
  const char *kind=argv[1];
  if(!strcmp(kind,"zero-decrement") || !strcmp(kind,"overread") || !strcmp(kind,"overwrite")) {
    long size=sysconf(_SC_PAGESIZE);if(size<64)return 2;
    size_t p=(size_t)size;
    unsigned char *mapping=mmap(NULL,p*3,PROT_NONE,MAP_PRIVATE|MAP_ANON,-1,0);
    if(mapping==MAP_FAILED)return 2;
    unsigned char *page=mapping+p;
    if(mprotect(page,p,PROT_READ|PROT_WRITE))return 2;
    for(size_t i=0;i<p;++i)page[i]=0xa5;
    unsigned char *src,*dst;size_t n;
    if(!strcmp(kind,"zero-decrement")){src=page;dst=page+1;n=0;}
    else if(!strcmp(kind,"overread")){src=page+p-1;dst=page+8;n=1;*src=0x55;}
    else {src=page+8;dst=page+p-1;n=1;*src=0x55;}
    void *result=vp2_memmove(dst,src,n);
    if(result!=dst || (n && *dst!=0x55))return 0;
    if(munmap(mapping,p*3))return 2;
    return 4; /* No violation observed: required result for the original code. */
  }
  unsigned char arena[64],before[64],expected[64];
  for(size_t i=0;i<sizeof(arena);++i)arena[i]=before[i]=expected[i]=(unsigned char)(37*i+11);
  size_t source,destination;
  if(!strcmp(kind,"always-forward") || !strcmp(kind,"reverse-direction")){source=16;destination=17;}
  else if(!strcmp(kind,"always-backward") || !strcmp(kind,"missing-first") || !strcmp(kind,"missing-last")) {source=17;destination=16;}
  else return 2;
  for(size_t i=0;i<2;++i)expected[destination+i]=before[source+i];
  void *result=vp2_memmove(arena+destination,arena+source,2);
  return result!=arena+destination || memcmp(arena,expected,sizeof(arena)) ? 0 : 4;
}
