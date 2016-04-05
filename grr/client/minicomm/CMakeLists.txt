cmake_minimum_required(VERSION 2.8)
SET(CMAKE_VERBOSE_MAKEFILE on)

project(grr_minicomm)

include_directories(../../..)
list(APPEND CMAKE_CXX_FLAGS "-std=c++0x ${CMAKE_CXX_FLAGS} -g")

add_library(core_lib
  ../../proto/jobs.pb.cc
  ../../proto/semantic.pb.cc
  comms_utils.cc
  compression.cc
  config.cc config.pb.cc
  crypto.cc
  message_queue.cc
  util.cc
)
set(core_lib_DEPS boost_regex crypto protobuf z)

add_library(http_comms_lib http_connection.cc resource_monitor.cc)
set(http_comms_lib_DEPS core_lib curl ${core_lib_DEPS})

add_library(subprocess_delegator_lib subprocess_delegator.cc)
set(subprocess_delegator_lib_DEPS core_lib ${core_lib_DEPS})

add_library(client_actions_lib client_action.cc client_action_dispatcher.cc
  ../../proto/sysinfo.pb.cc
  ../../proto/knowledge_base.pb.cc
  client_actions/dump_process_memory.cc
  client_actions/enumerate_filesystems.cc
  client_actions/enumerate_interfaces.cc
  client_actions/enumerate_users.cc
  client_actions/find.cc
  client_actions/fingerprint_file.cc
  client_actions/get_client_info.cc
  client_actions/get_configuration.cc
  client_actions/get_install_date.cc
  client_actions/get_library_versions.cc
  client_actions/get_platform_info.cc
  client_actions/grep.cc
  client_actions/list_directory.cc
  client_actions/list_processes.cc
  client_actions/stat_file.cc
  client_actions/delete_grr_temp_files.cc
  client_actions/transfer_buffer.cc
  file_contents.cc
  file_operations.cc
  paths.cc
  tempfiles.cc
)
set(set_client_actions_lib_DEPS core_lib ${core_lib_DEPS})

add_executable(minicomm client_main.cc client.cc)
set(minicom_external_DEPS
  ${http_comms_lib_DEPS}
  ${client_actions_lib_DEPS}
  ${core_lib_DEPS})
list(REMOVE_DUPLICATES minicom_external_DEPS)
target_link_libraries(minicomm
  core_lib
  http_comms_lib
  client_actions_lib
  ${minicom_external_DEPS}
)

install(TARGETS minicomm DESTINATION bin)

# Tests Libraries

find_package(GTest REQUIRED)
include_directories(${GTEST_INCLUDE_DIR})

add_library(test_helper_lib
  client_test_base.cc
  logging_control.cc
  test_util.cc)

set(test_helper_lib_DEPS gtest pthread)

add_executable(unit_tests grr_test_main.cc
  client_action_dispatcher_test.cc
  client_action_test.cc
  client_actions/delete_grr_temp_files_test.cc
  client_actions/enumerate_filesystems_test.cc
  client_actions/enumerate_interfaces_test.cc
  client_actions/enumerate_users_test.cc
  client_actions/find_test.cc
  client_actions/fingerprint_file_test.cc
  client_actions/get_platform_info_test.cc
  client_actions/grep_test.cc
  client_actions/list_directory_test.cc
  client_actions/list_processes_test.cc
  client_actions/transfer_buffer_test.cc
  comms_utils_test.cc
  compression_test.cc
  config_test.cc
  crypto_test.cc
  file_contents_test.cc
  file_operations_test.cc
  message_queue_test.cc
  paths_test.cc
#  subprocess_delegator_test.cc
  tempfiles_test.cc
  util_test.cc
)
set(unit_tests_external_DEPS
  ${client_actions_lib_DEPS}
  ${core_lib_DEPS}
  ${subprocess_delegator_lib_DEPS}
  ${test_helper_lib_DEPS})
list(REMOVE_DUPLICATES unit_tests_external_DEPS)
target_link_libraries(unit_tests
  client_actions_lib
  core_lib
  subprocess_delegator_lib
  test_helper_lib
  ${unit_tests_external_DEPS}
)
