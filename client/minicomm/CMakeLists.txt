cmake_minimum_required(VERSION 2.8)
SET(CMAKE_VERBOSE_MAKEFILE on)

project(grr_minicomm)

include_directories(../../..)
list(APPEND CMAKE_CXX_FLAGS "-std=c++0x ${CMAKE_CXX_FLAGS}")


add_library(util_lib util.cc)

add_library(compression_lib compression.cc)
target_link_libraries(compression_lib z)

add_library(crypto_lib crypto.cc)
target_link_libraries(crypto_lib crypto)

add_library(grr_proto_lib ../../proto/jobs.pb.cc ../../proto/semantic.pb.cc)
target_link_libraries(grr_proto_lib protobuf)

add_library(message_queue_lib message_queue.cc)
target_link_libraries(message_queue_lib grr_proto_lib)

add_library(config_lib config.cc config.pb.cc)
target_link_libraries(config_lib protobuf util_lib)

add_library(comms_utils_lib comms_utils.cc)
target_link_libraries(comms_utils_lib message_queue_lib crypto_lib config_lib
                      grr_proto_lib compression_lib)

add_library(http_connection_lib http_connection.cc)
target_link_libraries(http_connection_lib curl message_queue_lib config_lib
                      comms_utils_lib util_lib)

add_library(subprocess_delegator_lib subprocess_delegator.cc)
target_link_libraries(subprocess_delegator_lib config_lib protobuf)

add_library(client_lib client.cc)
target_link_libraries(client_lib comms_utils_lib config_lib http_connection_lib
                      message_queue_lib subprocess_delegator_lib)

add_executable(minicomm client_main.cc)
target_link_libraries(minicomm client_lib)

install(TARGETS minicomm DESTINATION bin)

# Tests Libraries

find_package(GTest REQUIRED)
include_directories(${GTEST_INCLUDE_DIR})

add_library(logging_control logging_control.cc)
target_link_libraries(logging_control protobuf)

add_library(client_test_base_lib client_test_base.cc)
target_link_libraries(client_test_base_lib logging_control)

# Tests for each component library

add_library(compression_test compression_test.cc)
target_link_libraries(compression_test gtest compression_lib)

add_library(comms_utils_test comms_utils_test.cc)
target_link_libraries(comms_utils_test gtest comms_utils_lib
                      client_test_base_lib)

add_library(config_test config_test.cc)
target_link_libraries(config_test gtest config_lib)

add_library(crypto_test crypto_test.cc)
target_link_libraries(crypto_test gtest crypto_lib)

add_library(message_queue_test message_queue_test.cc)
target_link_libraries(message_queue_test gtest message_queue_lib)

add_library(subprocess_delegator_test subprocess_delegator_test.cc)
target_link_libraries(subprocess_delegator_test gtest subprocess_delegator_lib
                      client_test_base_lib)

add_library(util_test util_test.cc)
target_link_libraries(util_test gtest util_lib)

# Build an executable with all tests.

add_executable(unit_tests grr_test_main.cc)
target_link_libraries(unit_tests gtest pthread logging_control
  -Wl,--whole-archive
    comms_utils_test
    compression_test
    config_test
    crypto_test
    message_queue_test
    subprocess_delegator_test
    util_test
  -Wl,--no-whole-archive)
