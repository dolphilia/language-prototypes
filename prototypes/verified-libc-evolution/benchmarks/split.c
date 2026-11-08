#define _POSIX_C_SOURCE 200809L
#include "vp2_calls.h"
#include "vp2_split.h"
#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>
#if VP_MODE == 2
typedef int (*selected_fn)(void *,size_t,size_t,size_t);
static selected_fn volatile selected=vp2_copy_split;
#else
typedef void *(*selected_fn)(void *,const void *,size_t);
static selected_fn volatile selected=
#if VP_MODE == 1
vp2_call_copy;
#else
vp2_memcpy_chunk8;
#endif
#endif
static uint64_t number(const char *s) {
  char *end;errno=0;unsigned long long n=strtoull(s,&end,10);
  if(errno || !*s || *end || *s=='-')exit(2);
  return n;
}
static uint64_t now(void) {
  struct timespec t;if(clock_gettime(CLOCK_MONOTONIC,&t))exit(2);
  return (uint64_t)t.tv_sec*1000000000+(uint64_t)t.tv_nsec;
}
int main(int argc,char **argv) {
  if(argc!=7 || strcmp(argv[6],"v1"))return 2;
  size_t capacity=number(argv[1]),split=number(argv[2]),n=number(argv[3]),alignment=number(argv[4]);
  uint64_t iterations=number(argv[5]);
  int valid=split>0 && split<capacity && n<=split && n<=capacity-split;
  if(capacity>2*1048576+64 || alignment>1 || !iterations)return 2;
#if VP_MODE != 2
  if(!valid)return 2;
#endif
  size_t stride=(capacity+128+63)&~(size_t)63;
  size_t arena_bytes=(valid && n>=32768)?128*1024*1024:stride,slots=arena_bytes/stride;
  unsigned char *arena;
  if(posix_memalign((void**)&arena,64,arena_bytes))return 3;
  for(size_t i=0;i<arena_bytes;++i)arena[i]=(unsigned char)(i*31+7);
  size_t transferred=valid?n:0;
  uint64_t warm=transferred?4194304/transferred:4096;
  if(warm>4096)warm=4096;
  if(!warm)warm=1;
  for(uint64_t i=0;i<warm;++i) {
    unsigned char *root=arena+(size_t)(i%slots)*stride+64+alignment;
#if VP_MODE == 2
    int status=selected(root,capacity,split,n);
    if(i==0 && status!=(valid?0:1))return 5;
#else
    void *result=selected(root+split,root,n);
    if(i==0 && result!=root+split)return 5;
#endif
  }
  uint64_t start=now();
  for(uint64_t i=0;i<iterations;++i) {
    unsigned char *root=arena+(size_t)(i%slots)*stride+64+alignment;
#if VP_MODE == 2
    selected(root,capacity,split,n);
#else
    selected(root+split,root,n);
#endif
  }
  uint64_t elapsed=now()-start,checksum=0;
  for(size_t slot=0;slot<slots;++slot) {
    unsigned char *root=arena+slot*stride+64+alignment;
    checksum+=root[0]+root[capacity?capacity-1:0];
    if(valid)checksum+=root[split]+root[split+(n?n-1:0)];
  }
  printf("{\"elapsed_ns\":%llu,\"iterations\":%llu,\"checksum\":%llu,"
         "\"arena_bytes\":%zu,\"slots\":%zu,\"stride\":%zu,\"warmup_calls\":%llu,"
         "\"transferred_bytes_per_call\":%zu,\"pid\":%d}\n",
    (unsigned long long)elapsed,(unsigned long long)iterations,(unsigned long long)checksum,
    arena_bytes,slots,stride,(unsigned long long)warm,transferred,(int)getpid());
  free(arena);return 0;
}
