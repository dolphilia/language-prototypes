#define _DARWIN_C_SOURCE
#include "vp2_split.h"
#include <stdint.h>
#include <string.h>
#include <sys/mman.h>
#include <unistd.h>
int main(int argc,char **argv) {
  if(argc!=2)return 2;
  long queried=sysconf(_SC_PAGESIZE);if(queried<=0)return 2;
  size_t page=(size_t)queried;
  unsigned char *mapping=mmap(0,3*page,PROT_NONE,MAP_PRIVATE|MAP_ANON,-1,0);
  if(mapping==MAP_FAILED || mprotect(mapping+page,page,PROT_READ|PROT_WRITE))return 2;
  unsigned char *arena=mapping+2*page-16,before[16],expected[16];
  for(size_t i=0;i<16;++i)arena[i]=before[i]=expected[i]=(unsigned char)i;
  size_t split,n;int status;
  if(!strcmp(argv[1],"split-range"))split=17,n=0,status=1;
  else if(!strcmp(argv[1],"input-length"))split=4,n=8,status=1;
  else if(!strcmp(argv[1],"output-length") || !strcmp(argv[1],"wrong-subtraction"))split=12,n=8,status=1;
  else if(!strcmp(argv[1],"overlap-target"))split=8,n=1,status=0,expected[8]=before[0];
  else return 2;
  int actual=vp2_copy_split(arena,16,split,n);
  int violation=actual!=status || memcmp(arena,expected,16)!=0;
  munmap(mapping,3*page);
  return violation?0:4;
}
