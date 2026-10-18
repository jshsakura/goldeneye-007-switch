/*
 * portaddr_runtime.h — runtime rebase support for platforms that cannot
 * provide the N64 memory map at its literal addresses (NRO/PIE loads).
 *
 * On Windows/Linux the port is linked no-PIE and maps the ROM/DRAM at the
 * exact PORT_* constants from portaddr.h. An NRO is position-independent:
 * the exe's own absolute references (dram_syms.S, romassets_<r>.s) are
 * rebased by the loader to load_base + constant. g_port_rebase holds that
 * load_base, and the mapping layer adds it to every PORT_* target so the
 * mapped memory sits exactly where the rebased pointers point.
 */
#ifndef PORT_PORTADDR_RUNTIME_H
#define PORT_PORTADDR_RUNTIME_H

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

extern uintptr_t g_port_rebase; /* 0 on no-PIE platforms */

static inline uintptr_t portRebaseAddr(uintptr_t addr)
{
    return addr + g_port_rebase;
}

#ifdef __cplusplus
}
#endif

#endif
