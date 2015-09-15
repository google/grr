#include "grr/client/minicomm/client_actions/list_processes.h"

#include <unistd.h>
#include <algorithm>
#include <fstream>

#include "gtest/gtest.h"
#include "grr/client/minicomm/file_operations.h"
#include "grr/client/minicomm/test_util.h"
#include "grr/client/minicomm/util.h"

namespace grr {
namespace actions {
namespace {

void WriteFile(const std::string& file_name, const std::string& data) {
  std::ofstream file;
  file.open(file_name);
  ASSERT_TRUE(file.good());
  file << data;
  file.close();
}

void CreateProcessDir(const std::string& dir, const Process& proc) {
  const std::string name = proc.name();
  const int pid = proc.pid();
  const int ppid = proc.ppid();
  const int threads = proc.num_threads();
  const std::string path = dir + "/" + std::to_string(pid);
  ASSERT_EQ(mkdir(path.c_str(), 0700), 0);
  WriteFile(path + "/status", "Name: " + name + "\n" + "Pid: " +
                                  std::to_string(pid) + "\n" + "PPid: " +
                                  std::to_string(ppid) + "\n" + "Threads: " +
                                  std::to_string(threads));

  WriteFile(path + "/cmdline", proc.cmdline(0) + '\0');
  const std::string path_exe_real = proc.exe();

  WriteFile(path_exe_real, "executable:data");
  const std::string path_exe = path + "/exe";
  ASSERT_EQ(symlink(path_exe_real.c_str(), path_exe.c_str()), 0);
}
}  // namespace

TEST(ListProcessesTest, ProcessRequest) {
  GrrMessage message;
  MessageQueue queue(1000, 20000);
  ActionContext context(message, &queue, nullptr);

  actions::ListProcesses action;
  action.ProcessRequest(&context);

  const auto r = queue.GetMessages(10, 20000, true);
  ASSERT_GT(r.size(), 0);
  for (const auto& m : r) {
    Process u;
    ASSERT_TRUE(u.ParseFromString(m.args()));
    GOOGLE_LOG(INFO) << u.DebugString();
  }
}

TEST(ListProcessesTest, PopulateProcessInfo) {
  const std::string temp_dir = testing::MakeTempDir();
  const int test_num = 10;
  const int test_int_parameters = 3;
  const int test_str_parameters = 3;

  Process proc[test_num];
  Process response[test_num];

  std::vector<int> rand_integers;
  std::vector<std::string> rand_strings;

  for (int i = 0; i < test_int_parameters * test_num; ++i) {
    rand_integers.push_back(i);
  }

  for (int i = 0; i < test_str_parameters * test_num; ++i) {
    const int len = 10;
    std::string str;
    for (int j = 0; j < len; ++j) {
      str += static_cast<char>(rand() % 26 + 'a');
    }

    rand_strings.push_back(str);
  }

  std::random_shuffle(rand_integers.begin(), rand_integers.end());
  std::random_shuffle(rand_strings.begin(), rand_strings.end());

  actions::ListProcesses action;
  Process tmp;
  std::string error;
  for (int i = 0; i < test_num; ++i) {
    proc[i].set_pid(rand_integers[i * test_int_parameters + 0]);
    proc[i].set_ppid(rand_integers[i * test_int_parameters + 1]);
    proc[i].set_num_threads(rand_integers[i * test_int_parameters + 2]);

    proc[i].set_name(rand_strings[i * test_str_parameters + 0]);
    // exe requires full path
    proc[i].set_exe(temp_dir + "/" + std::to_string(proc[i].pid()) + "/" +
                    rand_strings[i * test_str_parameters + 1]);
    proc[i].add_cmdline(rand_strings[i * test_str_parameters + 2]);

    CreateProcessDir(temp_dir, proc[i]);
    action.PopulateProcessInfo(temp_dir + "/" + std::to_string(proc[i].pid()),
                               response + i, &error);
  }

  std::set<std::string> original, output;
  for (int i = 0; i < test_num; ++i) {
    original.insert(proc[i].SerializeAsString());
    output.insert(response[i].SerializeAsString());
  }

  ASSERT_GT(original.size(), 0);
  ASSERT_EQ(original, output);
}
}  // namespace actions
}  // namespace grr
