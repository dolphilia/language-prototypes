#ifndef VP_MEMORY_H
#define VP_MEMORY_H
#include <stddef.h>
/* Non-NULL ordinary RAM, no concurrent modification/free, no address wrap.
 * memcpy requires disjoint ranges. dst must not overlap executable code.
 * n==0 performs no data access and still requires non-NULL pointers.
 * No stack/heap allocation. Return the original dst. */
void *vp_memcpy(void *dst, const void *src, size_t n);
void *vp_memcpy_scalar(void *dst, const void *src, size_t n);
void *vp_memset(void *dst, int c, size_t n);
#endif
