#include "grr/client/minicomm/client_actions/enumerate_users.h"

#include <pwd.h>

#include "grr/proto/knowledge_base.pb.h"
#include "grr/client/minicomm/base.h"
#include "grr/client/minicomm/util.h"
#include "grr/client/minicomm/file_operations.h"

// Needs to come after knowledge_base.pb.h due to name clash.
// TODO(user): Fix properly (put protos in namespace?).
#include <utmp.h>

namespace grr {
namespace actions {

void EnumerateUsers::ProcessRequest(ActionContext* args) {
  auto users = UsersFromWtmp("/var/log/wtmp");

  constexpr int kBuffSize = 32 * 1024;
  char buff[kBuffSize];
  struct passwd pwd;
  struct passwd* result;

  for (const auto& user : users) {
    User u;
    u.set_username(user.first);
    u.set_last_logon(std::max(0, user.second));
#ifdef ANDROID
    continue;
#else
    int s = getpwnam_r(user.first.c_str(), &pwd, buff, kBuffSize, &result);
    if (result != nullptr) {
      u.set_homedir(result->pw_dir);
      u.set_full_name(result->pw_gecos);
    }
#endif
    args->SendResponse(u, GrrMessage::MESSAGE);
  }
}

std::map<std::string, int32> EnumerateUsers::UsersFromWtmp(
    const std::string& wtmp) {
  std::map<std::string, int32> res;
  auto file = OpenedPath::Open(wtmp, nullptr);
  if (file != nullptr) {
    char buff[sizeof(utmp) * 100];
    size_t bytes_read;
    if (!file->Read(buff, &bytes_read, nullptr)) {
      return res;
    }
    utmp* utmp_buff = reinterpret_cast<utmp*>(buff);
    for (int i = 0; i < bytes_read / sizeof(utmp); i++) {
      const utmp& u = utmp_buff[i];
      if (u.ut_type == USER_PROCESS) {
        const std::string user = ArrayToString(u.ut_user);
        const std::string device = ArrayToString(u.ut_line);
        if (device.find("pts") != 0 && device.find("tty") != 0) {
          GOOGLE_LOG(ERROR) << "Apparent utmp mismatch, found login device: ["
                            << device << "]";
          continue;
        }
        auto it = res.find(user);
        if (it == res.end()) {
          res[user] = u.ut_tv.tv_sec;
        } else {
          it->second = std::max(it->second, static_cast<int32>(u.ut_tv.tv_sec));
        }
      }
    }
  }
  return res;
}
}  // namespace actions
}  // namespace grr
