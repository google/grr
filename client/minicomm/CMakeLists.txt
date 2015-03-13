cmake_minimum_required(VERSION 2.8)
SET(CMAKE_VERBOSE_MAKEFILE on)

project(grr_minicomm)

include_directories(../../..)
list(APPEND CMAKE_CXX_FLAGS "-std=c++0x ${CMAKE_CXX_FLAGS}")

set(compression_lib_SRCS compression.cc)
add_library(compression_lib ${compression_lib_SRCS})

set(http_connection_lib_SRCS http_connection.cc)
add_library(http_connection_lib ${http_connection_lib_SRCS})

set(config_lib_SRCS config.cc config.pb.cc)
add_library(config_lib ${config_lib_SRCS})

set(subprocess_delegator_lib_SRCS subprocess_delegator.cc)
add_library(subprocess_delegator_lib ${subprocess_delegator_lib_SRCS})

set(crypto_lib_SRCS crypto.cc)
add_library(crypto_lib ${crypto_lib_SRCS})

set(minicomm_SRCS client.cc client_main.cc comms_utils.cc util.cc logging_control.cc message_queue.cc ../../proto/jobs.pb.cc ../../proto/semantic.pb.cc)
add_executable(minicomm ${minicomm_SRCS})

set(minicomm_internal_libs compression_lib http_connection_lib config_lib subprocess_delegator_lib crypto_lib)
set(minicomm_external_libs gtest_main gtest pthread crypto protobuf curl z)
set(minicomm_libs ${minicomm_internal_libs} ${minicomm_external_libs})

target_link_libraries(minicomm ${minicomm_libs})

install(TARGETS minicomm DESTINATION bin)
