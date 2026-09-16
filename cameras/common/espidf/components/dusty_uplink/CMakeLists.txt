idf_component_register(
    SRCS "src/dusty_uplink.c"
    INCLUDE_DIRS "include"
    REQUIRES esp_http_client esp_wifi esp_netif esp_event esp-tls lwip
    PRIV_REQUIRES dusty_core log
)
