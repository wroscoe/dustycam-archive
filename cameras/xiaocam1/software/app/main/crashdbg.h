/* crashdbg: heap guard (always on) plus instrumentation for the 2026-09-15 xiaocam1 crash
 * (docs/crash_experiment_2026-09-16.md). Compiled out unless
 * CONFIG_DUSTY_CRASH_DEBUG is set (sdkconfig.crashdebug). */
#ifndef XIAOCAM1_CRASHDBG_H
#define XIAOCAM1_CRASHDBG_H

#include "sdkconfig.h"

/* Always compiled: check the internal heap's integrity and abort() if it is
 * damaged, so corruption panics near where it happened (and counts towards
 * crash_n / Recovery) instead of surfacing much later in an unrelated ISR,
 * as the 2026-09-15 stack overflow did. Cheap: headers/canaries only. */
void heap_guard(const char *where);

#ifdef CONFIG_DUSTY_CRASH_DEBUG
/* Log this task's stack high-water mark and check internal-heap integrity. */
void crashdbg_check(const char *where);
/* Log the esp_timer TCB's neighbours and arm a store-watchpoint on its
 * xEventListItem.pxContainer, on both CPUs. */
void crashdbg_arm_tcb_watch(void);
#define CRASHDBG(where) crashdbg_check(where)
#define CRASHDBG_ARM()  crashdbg_arm_tcb_watch()
#else
#define CRASHDBG(where) ((void)0)
#define CRASHDBG_ARM()  ((void)0)
#endif

#endif
