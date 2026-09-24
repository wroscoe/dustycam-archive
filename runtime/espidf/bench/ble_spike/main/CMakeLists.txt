idf_component_register(
    SRCS "main.c" "camera.c"
    INCLUDE_DIRS "."
    PRIV_REQUIRES
        esp32-camera
        dusty_core
        dusty_config
        dusty_uplink
        dusty_spool
        dusty_control
        dusty_ble
        driver
        esp_wifi
        esp_netif
        esp_event
        nvs_flash
        esp_timer
        esp_psram
        esp_hw_support
        esp_system
        heap
        json
)
