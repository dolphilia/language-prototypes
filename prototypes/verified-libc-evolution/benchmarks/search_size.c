#include "vp2_memory.h"
#ifndef VE_CANDIDATE
#error VE_CANDIDATE must name the selected candidate
#endif
extern void *VE_CANDIDATE(void *,const void *,size_t);
int main(int argc,char **argv) {
 (void)argv; unsigned char src[32]={0},dst[32]={0};
 VE_CANDIDATE(dst,src,(unsigned)argc%32);vp2_memset(dst,argc,32);return dst[0];
}
