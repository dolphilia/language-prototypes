#ifndef VP2_EVOLUTION_H
#define VP2_EVOLUTION_H
#include "vp2_memory.h"
/* Ordinary live RAM, non-NULL pointers, no address wrap, destination disjoint
 * from executable code, and exclusive updates remain caller obligations.
 * Source and destination may overlap; the result uses the initial source. */
void *vp2_memmove(void *dst, const void *src, size_t n);
#endif
