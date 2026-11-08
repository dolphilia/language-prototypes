#include "vp2_memory.h"
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <sys/mman.h>
#include <unistd.h>
typedef void *(*copy_fn)(void *,const void *,size_t);
extern void *vp2_invoke_x3_zero(copy_fn,void *,const void *,size_t);
extern int vp2_check_copy_abi(copy_fn,void *,const void *,size_t);

static unsigned char *page(size_t length) {
  void *p=mmap(NULL,length*3,PROT_NONE,MAP_ANON|MAP_PRIVATE,-1,0);
  if(p==MAP_FAILED || !p) return NULL;
  unsigned char *middle=(unsigned char*)p+length;
  if(mprotect(middle,length,PROT_READ|PROT_WRITE)) return NULL;
  return middle;
}
int main(int argc,char **argv) {
  if(argc!=2) return 2;
  long native_page=sysconf(_SC_PAGESIZE);if(native_page<=0) return 2;
  size_t length=(size_t)native_page;
  unsigned char *source=page(length),*dest=page(length);
  if(!source || !dest) return 3;
  memset(source,0x55,length);memset(dest,0xaa,length);
  if(!strcmp(argv[1],"return")) {
    if(vp2_invoke_x3_zero(vp2_memcpy_chunk8,dest,source,0)!=NULL) return 4;
    puts("non-NULL destination but returned NULL");return 0;
  }
  if(!strcmp(argv[1],"frame")) {
    if(vp2_check_copy_abi(vp2_memcpy_chunk8,dest,source,0)==0) return 5;
    puts("saved-register check detected corruption");return 0;
  }
  if(!strcmp(argv[1],"missing-tail")) {
    if(vp2_invoke_x3_zero(vp2_memcpy_chunk8,dest,source,1)!=dest || dest[0]!=0xaa) return 6;
    puts("one-byte copy returned without copying byte 0");return 0;
  }
  size_t n=!strcmp(argv[1],"short-word")?4:8;
  if(strcmp(argv[1],"decrease")) source+=length-8,dest+=length-8;
  /* The unmodified kernel succeeds at these same valid arguments. */
  vp2_invoke_x3_zero(vp2_memcpy_chunk8,dest,source,n);
  return 7; /* A guard mutation should fault in its own subprocess. */
}
