/*
 * Switch (libnx) mmap shim for the GoldenEye PC port.
 *
 * Horizon has no POSIX mmap. The port needs exactly three things:
 *   1. anonymous fixed-address RW mappings (romdata.c cart map)
 *   2. one backing store visible at two fixed addresses (dram.c V1 + K0)
 *   3. low anonymous RW allocations (thread stacks; falls back to heap)
 *
 * Implemented over svcCreateSharedMemory / svcMapSharedMemory, which is the
 * only libnx primitive that both picks the virtual address and supports
 * mapping the same region twice (the DRAM mirror).
 *
 * NOTE ON ADDRESSES: an NRO is position-independent; the loader rebases the
 * exe, so the "absolute" dram_syms.S / romassets_j.s constants effectively
 * become load_base + constant. romdata.c/dram.c therefore pass us
 * (load_base + PORT_..._BASE) as the mapping target (see portaddr_runtime.h),
 * and the mapped memory then lands exactly where the rebased pointers point.
 */
#ifndef PORT_SHIM_SYS_MMAN_H
#define PORT_SHIM_SYS_MMAN_H

#if !defined(__SWITCH__)
#include_next <sys/mman.h>
#else

#include <stdint.h>
#include <stddef.h>

#define PROT_NONE  0
#define PROT_READ  1
#define PROT_WRITE 2
#define MAP_SHARED   0x01
#define MAP_PRIVATE  0x02
#define MAP_ANONYMOUS 0x04
#define MAP_FIXED    0x10
#define MAP_FIXED_NOREPLACE MAP_FIXED
#define MAP_STACK    0x00 /* no-op on Horizon */
/* Do NOT define MAP_32BIT: libnx's pthread_create (threadCreate) already
 * maps thread stacks in StackRegion (0x08000000..0x80000000, < 2 GiB),
 * whereas the libnx heap is above 4 GiB. */
#define MAP_FAILED   ((void *)-1)

#ifdef __cplusplus
extern "C" {
#endif

void *mmap(void *addr, size_t length, int prot, int flags, int fd, long long offset);
int munmap(void *addr, size_t length);

#ifdef __cplusplus
}
#endif

#endif /* __SWITCH__ */

#endif
