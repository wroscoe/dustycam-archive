cmake_minimum_required(VERSION 3.16)

# PROJECT_VER must be set before project() to land in esp_app_desc.
file(STRINGS "${CMAKE_CURRENT_LIST_DIR}/version.txt" ver_lines)
list(GET ver_lines 0 PROJECT_VER)

set(EXTRA_COMPONENT_DIRS
    ${CMAKE_CURRENT_LIST_DIR}/../../components
)

include($ENV{IDF_PATH}/tools/cmake/project.cmake)
project(ble_spike)
