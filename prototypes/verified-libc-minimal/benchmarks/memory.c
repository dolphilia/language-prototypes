#define _POSIX_C_SOURCE 200809L
#include "vp_memory.h"
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

typedef void *(*copy_fn)(void *,const void *,size_t);
typedef void *(*fill_fn)(void *,int,size_t);
static copy_fn volatile selected_copy;
static fill_fn volatile selected_fill;
static uint64_t now(void) {
  struct timespec t;
  if(clock_gettime(CLOCK_MONOTONIC,&t)) exit(2);
  return (uint64_t)t.tv_sec*1000000000+(uint64_t)t.tv_nsec;
}
int main(int argc,char **argv) {
  if(argc!=7) return 2;
  const int fill=!strcmp(argv[1],"fill");
  size_t n=strtoull(argv[3],NULL,10),sa=strtoull(argv[4],NULL,10),da=strtoull(argv[5],NULL,10);
  uint64_t iterations=strtoull(argv[6],NULL,10);
  if(n>1024||sa>15||da>15||!iterations) return 2;
  _Alignas(64) unsigned char source[2048],dest[2048];
  for(size_t i=0;i<sizeof(source);++i) source[i]=(unsigned char)(i*31+7),dest[i]=0;
  if(fill) selected_fill=!strcmp(argv[2],"libc")?memset:vp_memset;
  else selected_copy=!strcmp(argv[2],"libc")?memcpy:
    (!strcmp(argv[2],"scalar")?vp_memcpy_scalar:vp_memcpy);
  for(size_t i=0;i<10000;++i) {
    if(fill) selected_fill(dest+da,0xa7,n); else selected_copy(dest+da,source+sa,n);
  }
  uint64_t start=now();
  if(fill) for(uint64_t i=0;i<iterations;++i) selected_fill(dest+da,0xa7,n);
  else for(uint64_t i=0;i<iterations;++i) selected_copy(dest+da,source+sa,n);
  uint64_t elapsed=now()-start,sum=0;
  for(size_t i=0;i<sizeof(dest);++i) sum+=dest[i]+source[i];
  printf("{\"elapsed_ns\":%llu,\"iterations\":%llu,\"checksum\":%llu}\n",
    (unsigned long long)elapsed,(unsigned long long)iterations,(unsigned long long)sum);
  return 0;
}
