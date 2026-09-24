idf_component_register(
    SRCS "src/dusty_spool.c"
    INCLUDE_DIRS "include"
    REQUIRES driver fatfs sdmmc
    PRIV_REQUIRES dusty_core log
)
