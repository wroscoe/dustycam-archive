/* cfg_src.c: config source/base tracking (docs/phone_app_plan.md §3).
 * Pure logic, no I/O -- dusty_config persists the two ints this operates
 * on; see runtime/espidf/tests/test_core.py for the host tests. */
#include "dusty_core.h"

void dc_cfg_src_on_local_edit(dc_cfg_src_t *s, int cfg_before)
{
    if (!s->cfg_src_is_ble) s->cfg_base = cfg_before;
    s->cfg_src_is_ble = 1;
}

void dc_cfg_src_on_server_sync(dc_cfg_src_t *s, int cfg)
{
    s->cfg_src_is_ble = 0;
    s->cfg_base = cfg;
}
