idf_component_register(
    SRCS "src/dusty_control.c"
    INCLUDE_DIRS "include"
    REQUIRES esp_http_server esp_timer
    PRIV_REQUIRES log esp_netif lwip
)
