#include "grr/client/minicomm/util.h"

#include <array>
#include <cctype>

#include "grr/client/minicomm/base.h"

namespace grr {
namespace {
constexpr std::array<char, 16> hex_digits = {{'0', '1', '2', '3', '4', '5', '6',
                                              '7', '8', '9', 'a', 'b', 'c', 'd',
                                              'e', 'f'}};
}
std::string BytesToHex(const std::string& input) {
  std::string output(2 * input.length(), '\0');
  for (int i = 0; i < input.length(); i++) {
    output[2 * i] = hex_digits[(input[i] >> 4) & 0x0F];
    output[2 * i + 1] = hex_digits[input[i] & 0x0F];
  }
  return output;
}
std::string UrlDirname(const std::string& input) {
  size_t end_slash = input.rfind('/');
  if (end_slash == std::string::npos) {
    GOOGLE_LOG(ERROR) << "Invalid URL:" << input;
    return "";
  }
  return input.substr(0, end_slash);
}

bool IsNumber(const std::string& x) {
  for (auto& c : x) {
    if (isdigit(c) == false) return false;
  }

  return true;
}

std::string ErrorName(int errnum) {
  char buff[1024];
// NOTE: The version of strerror_r that we get when including libstdc++ is GNU
// specific and may return buff, or may return pointer to a static string
// constant. In the latter case we trust the null termination, in the former
// case we hard limit the size of the string with ArrayToString just in case.

#ifdef ANDROID
  int res = strerror_r(errnum, buff, sizeof(buff));
  if (res == 0) {
    return ArrayToString(buff);
  }
  return "Error occured.";
#else
  char* res = strerror_r(errnum, buff, sizeof(buff));
  if (res == buff) {
    return ArrayToString(buff);
  }
  return res;
#endif
}
}  // namespace grr
