#include "vp2_calls.h"
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
typedef void *(*copy_fn)(void *,const void *,size_t);
extern int vp2_check_copy_abi(copy_fn,void *,const void *,size_t);
extern int vp2_check_call_stack_copy(copy_fn,void *,const void *,size_t);
static size_t checks;
#define CHECK(p) do { ++checks;if(!(p)){fprintf(stderr,"call failure line %d: %s\n",__LINE__,#p);exit(1);} } while(0)
static void test(size_t n,size_t sa,size_t da) {
  size_t extent=n+128;
  unsigned char source[extent],before[extent],destination[extent],expected[extent];
  for(size_t i=0;i<extent;++i){source[i]=before[i]=(unsigned char)(37*i+11);destination[i]=expected[i]=0xa5;}
  for(size_t i=0;i<n;++i)expected[32+da+i]=before[32+sa+i];
  for(unsigned variant=0;variant<3;++variant) {
    for(size_t i=0;i<extent;++i)destination[i]=0xa5;
    if(variant==0)CHECK(vp2_call_copy(destination+32+da,source+32+sa,n)==destination+32+da);
    else if(variant==1)CHECK(vp2_check_copy_abi(vp2_call_copy,destination+32+da,source+32+sa,n)==0);
    else CHECK(vp2_check_call_stack_copy(vp2_call_copy,destination+32+da,source+32+sa,n)==0);
    CHECK(memcmp(destination,expected,extent)==0);
    CHECK(memcmp(source,before,extent)==0);
  }
}
int main(void) {
  const size_t lengths[]={0,1,2,4,7,8,9,15,16,17,31,32,33,63,64,255,256,1024,4096};
  for(size_t n=0;n<sizeof(lengths)/sizeof(*lengths);++n)
    for(size_t sa=0;sa<8;++sa)for(size_t da=0;da<8;++da)test(lengths[n],sa,da);
  printf("native call-copy: %zu checks passed (contents/ABI/SP/16-byte-frame boundaries)\n",checks);
  return 0;
}
