#include "vp2_calls.h"
#include "vp2_split.h"
int main(void) {
  unsigned char arena[32]={0};
#if VP_MODE == 2
  return vp2_copy_split(arena,32,16,8);
#elif VP_MODE == 1
  return vp2_call_copy(arena+16,arena,8)!=arena+16;
#else
  return vp2_memcpy_chunk8(arena+16,arena,8)!=arena+16;
#endif
}
