#ifndef VP2_MEMORY_H
#define VP2_MEMORY_H
#include <stddef.h>
void *vp_memcpy_scalar(void *,const void *,size_t);
void *vp_memcpy(void *,const void *,size_t);
void *vp2_memcpy_chunk8(void *,const void *,size_t);
void *vp2_memset(void *,int,size_t);
#endif
