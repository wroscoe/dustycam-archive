idf_component_register(
    SRCS "src/dusty_led.c"
    INCLUDE_DIRS "include"
    REQUIRES driver
    PRIV_REQUIRES log
)
