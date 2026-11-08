#include "vp2_split.h"
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
typedef int (*split_fn)(void *,size_t,size_t,size_t);
extern int vp2_check_split_abi(split_fn,void *,size_t,size_t,size_t);
extern int vp2_check_call_stack_split(split_fn,void *,size_t,size_t,size_t);
static size_t checks;
#define CHECK(p) do { ++checks;if(!(p)){fprintf(stderr,"split failure line %d: %s\n",__LINE__,#p);exit(1);} } while(0)
static void test(size_t L,size_t split,size_t n,size_t offset) {
  size_t extent=L+128;
  unsigned char arena[extent],initial[extent],expected[extent];
  int valid=split>0 && split<L && n<=split && n<=L-split;
  for(size_t i=0;i<extent;++i)initial[i]=expected[i]=(unsigned char)(i*37+11);
  if(valid)for(size_t i=0;i<n;++i)expected[32+offset+split+i]=initial[32+offset+i];
  for(unsigned variant=0;variant<3;++variant) {
    memcpy(arena,initial,extent);
    if(variant==0)CHECK(vp2_copy_split(arena+32+offset,L,split,n)==(valid?0:1));
    else if(variant==1)CHECK(vp2_check_split_abi(vp2_copy_split,arena+32+offset,L,split,n)==0);
    else CHECK(vp2_check_call_stack_split(vp2_copy_split,arena+32+offset,L,split,n)==0);
    CHECK(memcmp(arena,expected,extent)==0);
  }
}
int main(void) {
  for(size_t L=0;L<=32;++L)for(size_t split=0;split<=L+2;++split)
    for(size_t n=0;n<=L+2;++n)for(size_t offset=0;offset<2;++offset)test(L,split,n,offset);
  const size_t lengths[]={0,1,7,8,9,15,16,17,31,32,33,63,64,255,256,1024,4096};
  for(size_t i=0;i<sizeof(lengths)/sizeof(*lengths);++i) {
    size_t n=lengths[i],L=2*n+64,split=n+32;
    for(size_t offset=0;offset<8;++offset) {
      test(L,split,n,offset);test(L,0,n,offset);test(L,L,n,offset);
      test(L,split,SIZE_MAX,offset);test(L,SIZE_MAX,0,offset);
      test(L,split,L-split+1,offset);test(L,split,split+1,offset);
    }
  }
  printf("native copy-split: %zu checks passed (runtime guards/status/arena/ABI/SP/frame)\n",checks);
  return 0;
}
