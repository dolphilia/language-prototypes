#include "vp2_evolution.h"
#include <inttypes.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>
typedef void *(*move_fn)(void *,const void *,size_t);
static move_fn volatile selected;
static uint64_t ns(void) { struct timespec t;if(clock_gettime(CLOCK_MONOTONIC,&t))exit(2);return (uint64_t)t.tv_sec*1000000000+(uint64_t)t.tv_nsec; }
static size_t number(const char *s) { char *end;unsigned long long n=strtoull(s,&end,10);if(!*s || *end)exit(2);return (size_t)n; }
int main(int argc,char **argv) {
  if(argc!=7)return 2;
  if(!strcmp(argv[1],"new"))selected=vp2_memmove;
  else if(!strcmp(argv[1],"libc"))selected=memmove;
  else return 2;
  size_t n=number(argv[2]),offset=number(argv[3]),iterations=number(argv[5]);
  char *end;long long signed_delta=strtoll(argv[4],&end,10);
  if(!*argv[4] || *end || n>1048576 || offset>7 || !iterations || iterations>UINT64_C(4294967296) ||
     signed_delta<-(long long)n-1 || signed_delta>(long long)n+1 || strcmp(argv[6],"v1"))return 2;
  ptrdiff_t delta=(ptrdiff_t)signed_delta;
  size_t stride=(3*n+256+63)&~(size_t)63;
  size_t bytes=n>=32768?128*1024*1024:stride,slots=bytes/stride;
  if(!slots)return 2;
  bytes=slots*stride;
  unsigned char *arena=malloc(bytes);if(!arena)return 2;
  for(size_t i=0;i<bytes;++i)arena[i]=(unsigned char)(37*i+11);
  size_t warmup=n?4194304/n:4096;if(warmup>4096)warmup=4096;
  for(size_t i=0;i<warmup;++i) {
    unsigned char *src=arena+(i%slots)*stride+n+64+offset;
    selected(src+delta,src,n);
  }
  uint64_t start=ns();
  if(slots==1) {
    unsigned char *src=arena+n+64+offset;
    for(size_t i=0;i<iterations;++i)selected(src+delta,src,n);
  } else
    for(size_t i=0;i<iterations;++i) {
      unsigned char *src=arena+(i%slots)*stride+n+64+offset;
      selected(src+delta,src,n);
    }
  uint64_t elapsed=ns()-start,checksum=0;
  for(size_t slot=0;slot<slots;++slot) {
    unsigned char *dst=arena+slot*stride+n+64+offset+delta;
    checksum=checksum*131+dst[0]+(n?dst[n-1]:0);
  }
  printf("{\"pid\":%ld,\"iterations\":%zu,\"elapsed_ns\":%" PRIu64 ",\"checksum\":%" PRIu64
         ",\"arena_bytes\":%zu,\"slots\":%zu,\"stride\":%zu,\"warmup_calls\":%zu}\n",
         (long)getpid(),iterations,elapsed,checksum,bytes,slots,stride,warmup);
  free(arena);return 0;
}
