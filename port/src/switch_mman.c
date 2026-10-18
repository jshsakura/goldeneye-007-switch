/*
 * switch_mman.c — Horizon implementation of the small mmap subset the port
 * needs (see port/shim/sys/mman.h). Uses svcMapMemory to map heap allocations
 * at fixed virtual addresses within StackRegion (0x08000000..0x80000000, < 2 GiB).
 */
#if defined(__SWITCH__)
#include <switch.h>
#include "switch_port_log.h"
#include <errno.h>
#include <string.h>
#include <stdio.h>
/* port/shim/stdlib.h shadows the host header for game TUs; pull the real
 * one by its generated absolute path so memalign/free are declared. */
#include "hoststdlib.h"
#include <malloc.h>
/* Our own mmap shim header (prot constants + prototypes). */
#include <sys/mman.h>

/* Defined here (only compiled into the switch build via the port/src glob).
 * See portaddr_runtime.h. */
uintptr_t g_port_rebase = 0;
FILE *g_pl_file = NULL;

#define MMAN_MAX_MAPPINGS 32

struct mman_rec {
    void *addr;
    size_t size;
    void *heap_mem; /* non-NULL for svcMapMemory mappings; NULL for plain heap */
    VirtmemReservation *rv;
};

static struct mman_rec s_recs[MMAN_MAX_MAPPINGS];

static struct mman_rec *find_free(void)
{
    for (int i = 0; i < MMAN_MAX_MAPPINGS; i++)
        if (!s_recs[i].addr)
            return &s_recs[i];
    return NULL;
}

static struct mman_rec *find_addr(void *addr)
{
    for (int i = 0; i < MMAN_MAX_MAPPINGS; i++)
        if (s_recs[i].addr == addr)
            return &s_recs[i];
    return NULL;
}

void *mmap(void *addr, size_t length, int prot, int flags, int fd, long long offset)
{
    (void)fd;
    (void)offset;
    (void)prot;

    plog("mmap: addr=%p len=0x%zx prot=%d flags=0x%x fixed=%d",
         addr, length, prot, flags, !!(flags & MAP_FIXED));

    if (length == 0)
        return MAP_FAILED;

    struct mman_rec *rec = find_free();
    if (!rec) {
        plog("mmap: out of s_recs slots");
        errno = ENOMEM;
        return MAP_FAILED;
    }

    const size_t page = 0x1000;
    size_t aligned = (length + page - 1) & ~(page - 1);

    if (flags & MAP_FIXED) {
        /* Fixed-address mapping backed by heap memory and mapped via svcMapMemory. */
        void *heap_mem = memalign(page, aligned);
        if (!heap_mem) {
            plog("mmap: memalign FAILED: size=0x%zx", aligned);
            errno = ENOMEM;
            return MAP_FAILED;
        }

        virtmemLock();
        VirtmemReservation *rv = virtmemAddReservation(addr, aligned);
        Result rc = svcMapMemory(addr, heap_mem, aligned);
        virtmemUnlock();

        if (R_FAILED(rc)) {
            plog("svcMapMemory FAILED: rc=0x%x addr=%p heap=%p size=0x%zx",
                 rc, addr, heap_mem, aligned);
            if (rv) {
                virtmemLock();
                virtmemRemoveReservation(rv);
                virtmemUnlock();
            }
            free(heap_mem);
            errno = EACCES;
            return MAP_FAILED;
        }

        plog("svcMapMemory OK: addr=%p heap=%p size=0x%zx", addr, heap_mem, aligned);
        rec->addr = addr;
        rec->size = aligned;
        rec->heap_mem = heap_mem;
        rec->rv = rv;
        return addr;
    }

    /* Anonymous non-fixed: plain aligned heap. */
    void *p = memalign(page, aligned);
    plog("mmap non-fixed memalign: p=%p size=0x%zx", p, aligned);
    if (!p) {
        errno = ENOMEM;
        return MAP_FAILED;
    }
    memset(p, 0, aligned);
    rec->addr = p;
    rec->size = aligned;
    rec->heap_mem = NULL;
    rec->rv = NULL;
    return p;
}

int munmap(void *addr, size_t length)
{
    (void)length;
    struct mman_rec *rec = find_addr(addr);
    if (!rec) {
        errno = EINVAL;
        return -1;
    }

    if (rec->heap_mem) {
        virtmemLock();
        if (rec->rv) {
            virtmemRemoveReservation(rec->rv);
            rec->rv = NULL;
        }
        Result rc = svcUnmapMemory(rec->addr, rec->heap_mem, rec->size);
        virtmemUnlock();
        if (R_FAILED(rc)) {
            plog("svcUnmapMemory FAILED: rc=0x%x addr=%p", rc, rec->addr);
        }
        free(rec->heap_mem);
    } else {
        free(addr);
    }

    rec->addr = NULL;
    rec->size = 0;
    rec->heap_mem = NULL;
    rec->rv = NULL;
    return 0;
}

/*
 * Switch DRAM mapping helper: allocates heap backing store and maps it
 * at base1 (PORT_DRAM_V1_BASE = 0x20000000) using svcMapMemory.
 */
void *switchMapDramDual(uintptr_t base1, uintptr_t base2, size_t size)
{
    (void)base2;
    const size_t page = 0x1000;
    size_t aligned = (size + page - 1) & ~(page - 1);

    plog("dramDual: base1=%p base2=%p size=0x%zx", (void*)base1, (void*)base2, size);

    void *heap_mem = memalign(page, aligned);
    if (!heap_mem) {
        plog("dramDual: memalign FAILED: size=0x%zx", aligned);
        return NULL;
    }

    virtmemLock();
    VirtmemReservation *rv = virtmemAddReservation((void *)base1, aligned);
    Result rc = svcMapMemory((void *)base1, heap_mem, aligned);
    virtmemUnlock();

    if (R_FAILED(rc)) {
        plog("dramDual: svcMapMemory(base1) FAILED: rc=0x%x addr=%p heap=%p size=0x%zx",
             rc, (void *)base1, heap_mem, aligned);
        if (rv) {
            virtmemLock();
            virtmemRemoveReservation(rv);
            virtmemUnlock();
        }
        free(heap_mem);
        return NULL;
    }

    struct mman_rec *r1 = find_free();
    if (r1) {
        r1->addr = (void *)base1;
        r1->size = aligned;
        r1->heap_mem = heap_mem;
        r1->rv = rv;
    }

    memset((void *)base1, 0, aligned);
    plog("dramDual: mapped OK at %p (heap=%p, size=0x%zx)", (void*)base1, heap_mem, aligned);

    return (void *)base1;
}

#endif /* __SWITCH__ */
