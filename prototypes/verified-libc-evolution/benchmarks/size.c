#include "vp2_memory.h"
#ifndef VP_COPY
#define VP_COPY vp2_memcpy_chunk8
#endif
int main(int argc,char **argv) {
  (void)argv;
  unsigned char src[32]={0},dst[32]={0};
  VP_COPY(dst,src,(unsigned)argc%32);
  vp2_memset(dst,argc,32);
  return dst[0];
}
