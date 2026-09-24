idf_component_register(SRCS "main.c" "pt_core.c"
                       INCLUDE_DIRS "."
                       PRIV_REQUIRES driver fatfs sdmmc esp_timer nvs_flash)
