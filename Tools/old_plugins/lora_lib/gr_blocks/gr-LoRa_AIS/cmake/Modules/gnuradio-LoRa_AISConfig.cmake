find_package(PkgConfig)

PKG_CHECK_MODULES(PC_GR_LORA_AIS gnuradio-LoRa_AIS)

FIND_PATH(
    GR_LORA_AIS_INCLUDE_DIRS
    NAMES gnuradio/LoRa_AIS/api.h
    HINTS $ENV{LORA_AIS_DIR}/include
        ${PC_LORA_AIS_INCLUDEDIR}
    PATHS ${CMAKE_INSTALL_PREFIX}/include
          /usr/local/include
          /usr/include
)

FIND_LIBRARY(
    GR_LORA_AIS_LIBRARIES
    NAMES gnuradio-LoRa_AIS
    HINTS $ENV{LORA_AIS_DIR}/lib
        ${PC_LORA_AIS_LIBDIR}
    PATHS ${CMAKE_INSTALL_PREFIX}/lib
          ${CMAKE_INSTALL_PREFIX}/lib64
          /usr/local/lib
          /usr/local/lib64
          /usr/lib
          /usr/lib64
          )

include("${CMAKE_CURRENT_LIST_DIR}/gnuradio-LoRa_AISTarget.cmake")

INCLUDE(FindPackageHandleStandardArgs)
FIND_PACKAGE_HANDLE_STANDARD_ARGS(GR_LORA_AIS DEFAULT_MSG GR_LORA_AIS_LIBRARIES GR_LORA_AIS_INCLUDE_DIRS)
MARK_AS_ADVANCED(GR_LORA_AIS_LIBRARIES GR_LORA_AIS_INCLUDE_DIRS)
