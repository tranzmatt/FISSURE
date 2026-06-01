# Copyright 2020 Free Software Foundation, Inc.
#
# This file is part of GNU Radio
#
# SPDX-License-Identifier: GPL-3.0-or-later
#

########################################################################
# Check if there is C++ code at all
########################################################################
if(NOT LoRa_AIS_sources)
    message(STATUS "No C++ sources... skipping python bindings")
    return()
endif(NOT LoRa_AIS_sources)

########################################################################
# Check for pygccxml
########################################################################
gr_python_check_module_raw("pygccxml" "import pygccxml" PYGCCXML_FOUND)

include(GrPybind)

########################################################################
# Python Bindings
########################################################################

list(APPEND LoRa_AIS_python_files python_bindings.cc)

gr_pybind_make_oot(LoRa_AIS ../../.. gr::LoRa_AIS "${LoRa_AIS_python_files}")

# copy bindings extension for use in QA test module
add_custom_command(
    TARGET LoRa_AIS_python
    POST_BUILD
    COMMAND ${CMAKE_COMMAND} -E copy $<TARGET_FILE:LoRa_AIS_python>
            ${PROJECT_BINARY_DIR}/test_modules/gnuradio/LoRa_AIS/)

install(
    TARGETS LoRa_AIS_python
    DESTINATION ${GR_PYTHON_DIR}/gnuradio/LoRa_AIS
    COMPONENT pythonapi)
