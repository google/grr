#include "google/protobuf/stubs/common.h"
#include "gtest/gtest.h"

#include "grr/client/minicomm/logging_control.h"

int main(int argc, char **argv) {
  grr::LogControl::Initialize();
  testing::InitGoogleTest(&argc, argv);
  int r = RUN_ALL_TESTS();
  google::protobuf::ShutdownProtobufLibrary();
  return r;
}
