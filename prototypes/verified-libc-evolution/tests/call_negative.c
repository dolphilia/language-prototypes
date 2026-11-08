#include "vp2_calls.h"
#include <string.h>
typedef void *(*copy_fn)(void *,const void *,size_t);
extern int vp2_check_copy_abi(copy_fn,void *,const void *,size_t);
extern int vp2_check_call_stack_copy(copy_fn,void *,const void *,size_t);
int main(int argc,char **argv) {
  unsigned char src[32]={1,2,3,4},dst[32]={0};
  if(argc!=2)return 2;
  if(!strcmp(argv[1],"stack"))return vp2_check_call_stack_copy(vp2_call_copy,dst,src,0)?0:4;
  if(!strcmp(argv[1],"register"))return vp2_check_copy_abi(vp2_call_copy,dst,src,0)?0:4;
  if(!strcmp(argv[1],"return")){vp2_call_copy(dst,src,0);return 4;}
  return 2;
}
