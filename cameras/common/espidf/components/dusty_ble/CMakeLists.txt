idf_component_register(
    SRCS "src/ble_frame.c" "src/dusty_ble.c" "src/ble_auth.c"
    INCLUDE_DIRS "include"
    REQUIRES bt nvs_flash
    PRIV_REQUIRES mbedtls esp_timer esp_hw_support freertos heap log json
)
# ble_frame.c is portable/host-tested (cameras/common/espidf/tests/
# test_ble_frame.py via host/Makefile) and deliberately does not need any
# of the above -- it is only built into this component for firmware use.
#
# dusty_config is NOT a dependency yet: P0 answers cfg.*/prov.*/wifi.scan
# with err:unsupported unconditionally (docs/phone_app_plan.md P0 scope);
# P1 wires cfg.get/set/schema and prov.set to dusty_config and adds it here.

