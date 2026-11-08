#ifndef VP2_CALLS_H
#define VP2_CALLS_H
#include "vp2_evolution.h"
/* Same nonoverlapping ordinary-RAM contract as vp2_memcpy_chunk8, with a
 * separate 16-byte private stack frame in a valid aligned Apple arm64 ABI. */
void *vp2_call_copy(void *dst,const void *src,size_t n);
#endif
