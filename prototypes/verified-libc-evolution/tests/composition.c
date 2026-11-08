#include <stddef.h>
#include <stdio.h>
#include <string.h>

/* Experimental fixed-size blocks: the third argument is ignored in assembly.
   Giving it the same ABI signature permits the existing saved-state harness. */
typedef void *(*fixed_fn)(void *,const void *,size_t);
extern void *vp2_copy16(void *,const void *,size_t);
extern void *vp2_copy32(void *,const void *,size_t);
extern void *vp2_copy16_x3(void *,const void *,size_t);
extern int vp2_check_copy_abi(fixed_fn,void *,const void *,size_t);
int main(void) {
  _Alignas(64) unsigned char source[128],dest[128],reference[128];
  fixed_fn functions[]={vp2_copy16,vp2_copy32,vp2_copy16_x3};
  size_t lengths[]={16,32,16},checks=0;
  for(size_t f=0;f<3;++f) for(size_t sa=0;sa<64;sa+=8)
    for(size_t da=0;da<64;da+=8) {
      for(size_t i=0;i<sizeof source;++i) source[i]=(unsigned char)(i*31+f);
      memset(dest,0xaa,sizeof dest);memset(reference,0xaa,sizeof reference);
      memcpy(reference+da,source+sa,lengths[f]);
      if(functions[f](dest+da,source+sa,lengths[f])!=dest+da ||
         memcmp(dest,reference,sizeof dest) ||
         vp2_check_copy_abi(functions[f],dest+da,source+sa,lengths[f])) return 1;
      ++checks;
    }
  printf("native fixed compositions: %zu full-buffer/return/ABI cases passed\n",checks);
  return 0;
}
