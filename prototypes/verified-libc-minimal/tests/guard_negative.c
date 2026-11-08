#include "vp_memory.h"
#include <sys/mman.h>
#include <sys/resource.h>
#include <unistd.h>

/* Compile the same harness with a verified object or a deliberately bad one.
 * Only SIGSEGV/SIGBUS is accepted as the negative result by the Python driver. */
int main(void) {
  struct rlimit limit={0,0};
  if(setrlimit(RLIMIT_CORE,&limit)) return 2;
  long p=sysconf(_SC_PAGESIZE);
  if(p<=0) return 2;
  unsigned char *s=mmap(0,(size_t)p*2,PROT_NONE,MAP_ANON|MAP_PRIVATE,-1,0);
  unsigned char *d=mmap(0,(size_t)p*2,PROT_NONE,MAP_ANON|MAP_PRIVATE,-1,0);
  if(s==MAP_FAILED||d==MAP_FAILED) return 2;
  if(mprotect(s,(size_t)p,PROT_READ|PROT_WRITE)||
     mprotect(d,(size_t)p,PROT_READ|PROT_WRITE)) return 2;
  s[p-1]=0xa5;
  void *ret=vp_memcpy_scalar(d+p-1,s+p-1,1);
  int ok=ret==d+p-1&&d[p-1]==0xa5;
  if(munmap(s,(size_t)p*2)||munmap(d,(size_t)p*2)) return 2;
  return ok?0:3;
}
