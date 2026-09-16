idf_component_register(
    SRCS "main.c" "gate.cc" "gate_model_data.cc"
         "app_state.c" "camera.c" "judge.c" "telemetry.c" "contact.c" "radio.c" "crashdbg.c"
    INCLUDE_DIRS "."
    PRIV_REQUIRES
        esp32-camera
        esp-tflite-micro
        dusty_core
        dusty_uplink
        dusty_spool
        dusty_config
        dusty_ota
        dusty_led
        dusty_control
        dusty_ble
        json
        driver
        esp_wifi
        esp_netif
        esp_event
        nvs_flash
        app_update
        esp_timer
        esp_https_ota
        esp_http_client
        esp_psram
        esp_hw_support
        esp_system
)
