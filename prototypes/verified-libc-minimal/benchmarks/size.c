#include "vp_memory.h"
#include <stdlib.h>
int main(int argc,char **argv) {
  unsigned char src[256]={1},dst[256]={0};
  size_t n=argc>1?(size_t)strtoul(argv[1],0,10)%256:8;
  vp_memcpy(dst,src,n); vp_memset(dst+128,7,n%128);
  return dst[0]==255;
}
