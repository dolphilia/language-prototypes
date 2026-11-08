#include <stdio.h>

extern void vp_probe_ret(void);

int main(void) {
    vp_probe_ret();
    puts("P0: ret function called from C");
    return 0;
}
