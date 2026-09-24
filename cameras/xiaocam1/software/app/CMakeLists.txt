cmake_minimum_required(VERSION 3.16)

# PROJECT_VER must be set before project() to land in esp_app_desc.
file(STRINGS "${CMAKE_CURRENT_LIST_DIR}/version.txt" ver_lines)
list(GET ver_lines 0 PROJECT_VER)

set(EXTRA_COMPONENT_DIRS
    ${CMAKE_CURRENT_LIST_DIR}/../../../../runtime/espidf/components
)

# dusty_ble (docs/phone_app_plan.md P1) is now a real dependency (main/
# CMakeLists.txt PRIV_REQUIRES) -- CONFIG_BT_ENABLED etc. come from the
# NimBLE sdkconfig block in sdkconfig.defaults below. It used to be
# excluded here during P0 (bt wasn't enabled yet, so dusty_ble.c failed to
# compile -- ESP-IDF builds every component it *finds* under
# EXTRA_COMPONENT_DIRS regardless of REQUIRES, so it doesn't matter that
# nothing referenced it back then).

include($ENV{IDF_PATH}/tools/cmake/project.cmake)
project(xiaocam1)
