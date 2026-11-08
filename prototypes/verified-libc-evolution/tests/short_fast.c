#include "vp2_memory.h"
#include <stdio.h>
#include <string.h>
int main(void) {
 _Alignas(8) unsigned char src[16],dst[16];
 memset(src,0x55,sizeof src);memset(dst,0xaa,sizeof dst);
 if(vp_memcpy(dst,src,4)!=dst) return 1;
 for(size_t i=0;i<4;++i) if(dst[i]!=0x55) return 2;
 for(size_t i=4;i<8;++i) if(dst[i]!=0x55) return 3;
 for(size_t i=8;i<16;++i) if(dst[i]!=0xaa) return 4;
 puts("short-fast native sentinel: bytes 4..7 overwritten (contract violation)");
 return 0;
}
