#ifndef GRR_CLIENT_MINICOMM_UTIL_H_
#define GRR_CLIENT_MINICOMM_UTIL_H_

#include <string>

namespace grr {
std::string BytesToHex(const std::string& input);
std::string UrlDirname(const std::string& input);
}

#endif  // GRR_CLIENT_MINICOMM_UTIL_H_
