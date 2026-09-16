idf_component_register(
    SRCS "src/dusty_config.c"
    INCLUDE_DIRS "include"
    REQUIRES dusty_core nvs_flash
    PRIV_REQUIRES log
)
