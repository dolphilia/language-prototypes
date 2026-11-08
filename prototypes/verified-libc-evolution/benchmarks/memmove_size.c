#include "vp2_evolution.h"
#include <string.h>
int main(void) {
  unsigned char arena[32];
  for(size_t i=0;i<sizeof(arena);++i)arena[i]=(unsigned char)i;
  void *(*volatile move)(void *,const void *,size_t)=vp2_memmove;
  if(move(arena+1,arena,16)!=arena+1)return 2;
  return arena[16]!=15;
}
