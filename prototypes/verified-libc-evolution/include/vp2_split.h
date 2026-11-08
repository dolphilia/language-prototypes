#ifndef VP2_SPLIT_H
#define VP2_SPLIT_H
#include "vp2_evolution.h"
/* arena owns L bytes of valid, live, exclusive ordinary RAM. It is separated
 * from code and the valid private 16-byte stack. Return 0 iff
 * 0 < split < L && n <= split && n <= L-split; copy the initial first n bytes
 * to arena+split on success. Return 1 with arena unchanged on failure.
 * These are runtime checks: arbitrary size_t inputs are accepted. */
int vp2_copy_split(void *arena,size_t L,size_t split,size_t n);
#endif
