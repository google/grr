#ifndef GRR_CLIENT_MINICOMM_UTIL_H_
#define GRR_CLIENT_MINICOMM_UTIL_H_

#include <string.h>
#include <string>

namespace grr {
std::string BytesToHex(const std::string& input);
std::string UrlDirname(const std::string& input);
bool IsNumber(const std::string& x);

// Slightly paranoid conversion of a null terminated character array to a
// string: does the right thing if the null was truncated.
template <int size>
std::string ArrayToString(const char(&array)[size]) {
  return std::string(array, strnlen(array, size));
}

// Wrapper to convert C errno into string descriptions.
std::string ErrorName(int errnum);

}  // namespace grr

#endif  // GRR_CLIENT_MINICOMM_UTIL_H_
