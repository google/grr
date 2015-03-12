#ifndef EXPERIMENTAL_USERS_BGALEHOUSE_GRR_CPP_CLIENT_COMPRESSION_H_
#define EXPERIMENTAL_USERS_BGALEHOUSE_GRR_CPP_CLIENT_COMPRESSION_H_

#include <string>

namespace grr {
class ZLib {
 public:
  static std::string Inflate(const std::string& input);
  static std::string Deflate(const std::string& input);
};
}

#endif  // EXPERIMENTAL_USERS_BGALEHOUSE_GRR_CPP_CLIENT_COMPRESSION_H_
