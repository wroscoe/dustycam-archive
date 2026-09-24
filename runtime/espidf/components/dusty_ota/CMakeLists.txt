idf_component_register(
    SRCS "src/dusty_ota.c"
    INCLUDE_DIRS "include"
    REQUIRES esp_https_ota app_update esp_http_client esp_app_format esp-tls nvs_flash
    PRIV_REQUIRES dusty_core log
)
