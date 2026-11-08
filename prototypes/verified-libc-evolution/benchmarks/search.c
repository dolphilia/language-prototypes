#define _POSIX_C_SOURCE 200809L
#include "vp2_memory.h"
#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>

#ifndef VE_CANDIDATE
#error VE_CANDIDATE must name the frozen candidate
#endif
#ifndef VE_ORIGINAL
#define VE_ORIGINAL vp2_memcpy_chunk8
#endif
#ifndef VE_DATA_SEED
#error VE_DATA_SEED must distinguish exploration from confirmation
#endif
extern void *VE_CANDIDATE(void *,const void *,size_t);
extern void *VE_ORIGINAL(void *,const void *,size_t);

typedef void *(*copy_fn)(void *,const void *,size_t);
static copy_fn volatile selected;
static uint64_t now(void) {
  struct timespec t;
  if(clock_gettime(CLOCK_MONOTONIC,&t)) exit(2);
  return (uint64_t)t.tv_sec*1000000000+(uint64_t)t.tv_nsec;
}
static uint64_t number(const char *s) {
  char *end; errno=0;
  unsigned long long n=strtoull(s,&end,10);
  if(errno || !*s || *end || *s=='-') exit(2);
  return n;
}
int main(int argc,char **argv) {
  if(argc!=6) return 2;
  if(!strcmp(argv[1],"candidate")) selected=VE_CANDIDATE;
  else if(!strcmp(argv[1],"original")) selected=VE_ORIGINAL;
  else if(!strcmp(argv[1],"scalar")) selected=vp_memcpy_scalar;
  else if(!strcmp(argv[1],"exact8")) selected=vp_memcpy;
  else if(!strcmp(argv[1],"chunk8")) selected=VE_ORIGINAL;
  else if(!strcmp(argv[1],"libc")) selected=memcpy;
  else return 2;
  size_t n=number(argv[2]),sa=number(argv[3]),da=number(argv[4]);
  uint64_t iterations=number(argv[5]);
  if(n>1048576 || sa>7 || da>7 || !iterations) return 2;
  size_t stride=(n+128+63)&~(size_t)63;
  /* Two 64 MiB arenas, combined <=128 MiB. Small cases reuse one slot. */
  size_t arena=n>=32768?64*1024*1024:stride;
  size_t slots=arena/stride;
  unsigned char *source,*destination;
  if(posix_memalign((void**)&source,64,arena) ||
     posix_memalign((void**)&destination,64,arena)) return 3;
  for(size_t i=0;i<arena;++i) source[i]=(unsigned char)(i*31+(VE_DATA_SEED&255)),destination[i]=0;
  uint64_t warm=n?4194304/n:4096;
  if(warm>4096) warm=4096;
  if(!warm) warm=1;
  for(uint64_t i=0;i<warm;++i) {
    size_t offset=(size_t)(i%slots)*stride;
    selected(destination+offset+da,source+offset+sa,n);
  }
  uint64_t start=now();
  for(uint64_t i=0;i<iterations;++i) {
    size_t offset=(size_t)(i%slots)*stride;
    selected(destination+offset+da,source+offset+sa,n);
  }
  uint64_t elapsed=now()-start,checksum=0;
  for(size_t i=0;i<arena;i+=4096) checksum+=destination[i]+source[i];
  for(size_t slot=0;slot<slots;++slot) {
    size_t offset=slot*stride;
    checksum+=destination[offset+da]+destination[offset+da+(n?n-1:0)];
  }
  printf("{\"elapsed_ns\":%llu,\"iterations\":%llu,\"checksum\":%llu,"
         "\"arena_bytes\":%zu,\"slots\":%zu,\"warmup_calls\":%llu,\"pid\":%d}\n",
    (unsigned long long)elapsed,(unsigned long long)iterations,
    (unsigned long long)checksum,arena*2,slots,(unsigned long long)warm,(int)getpid());
  free(source);free(destination);
  return 0;
}
