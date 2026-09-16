#include "crashdbg.h"

#include <stdlib.h>

#include "esp_log.h"
#include "esp_heap_caps.h"

void heap_guard(const char *where)
{
    if (!heap_caps_check_integrity(MALLOC_CAP_INTERNAL, true)) {
        ESP_LOGE("heap_guard", "internal heap corrupt at \"%s\" -- aborting", where);
        abort();
    }
}

#ifdef CONFIG_DUSTY_CRASH_DEBUG
#include <stdint.h>

#include "esp_log.h"
#include "esp_cpu.h"
#include "esp_ipc.h"
#include "esp_heap_caps.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

static const char *TAG = "crashdbg";

/* TCB layout (vanilla FreeRTOS kernel, no MPU wrappers, no list integrity
 * bytes): pxTopOfStack (4) + xStateListItem (20) + xEventListItem's
 * pxContainer at +16 = 40. The assert in vTaskGenericNotifyGiveFromISR
 * (tasks.c:6213) reads exactly this field. */
#if configUSE_LIST_DATA_INTEGRITY_CHECK_BYTES || portUSING_MPU_WRAPPERS
#error "crashdbg: TCB offset 40 assumes no list integrity bytes and no MPU wrappers"
#endif
#define TCB_EVENT_CONTAINER_OFFSET 40

/* Watchpoint 1 belongs to CONFIG_FREERTOS_WATCHPOINT_END_OF_STACK
 * (STACK_WATCH_POINT_NUMBER = SOC_CPU_WATCHPOINTS_NUM - 1), re-armed on
 * every context switch. The TCB watch takes watchpoint 0. */
#define TCB_WATCHPOINT 0

void crashdbg_check(const char *where)
{
    UBaseType_t hwm = uxTaskGetStackHighWaterMark(NULL); /* bytes on ESP-IDF */
    bool ok = heap_caps_check_integrity(MALLOC_CAP_INTERNAL, true);
    ESP_LOGW(TAG, "[%s] task=%s stack_hwm=%u B internal_free=%u heap_ok=%d",
             where, pcTaskGetName(NULL), (unsigned)hwm,
             (unsigned)heap_caps_get_free_size(MALLOC_CAP_INTERNAL), ok ? 1 : 0);
}

static void arm_wp(void *arg)
{
    esp_cpu_set_watchpoint(TCB_WATCHPOINT, arg, 4, ESP_CPU_WATCHPOINT_STORE);
}

void crashdbg_arm_tcb_watch(void)
{
    TaskHandle_t t = xTaskGetHandle("esp_timer");
    ESP_LOGW(TAG, "esp_timer tcb=%p  this task (%s) stack start=%p",
             t, pcTaskGetName(NULL), pxTaskGetStackStart(NULL));
    heap_caps_dump(MALLOC_CAP_INTERNAL);
    if (!t) {
        ESP_LOGE(TAG, "no esp_timer task handle, watchpoint not armed");
        return;
    }
    void *field = (uint8_t *)t + TCB_EVENT_CONTAINER_OFFSET;
    /* esp_timer's task only ever blocks on a notification, so this should
     * be NULL now; non-NULL means the TCB is already damaged. */
    void *cur = *(void **)field;
    ESP_LOGW(TAG, "esp_timer xEventListItem.pxContainer @%p = %p (%s)",
             field, cur, cur ? "ALREADY CORRUPT" : "clean");
    arm_wp(field);
    esp_ipc_call_blocking(1, arm_wp, field);
    ESP_LOGW(TAG, "store-watchpoint %d armed on both CPUs", TCB_WATCHPOINT);
}
#endif
