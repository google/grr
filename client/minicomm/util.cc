#include "util.h"

#include <array>

#include "base.h"

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
}  // namespace grr
