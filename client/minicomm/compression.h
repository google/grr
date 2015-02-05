#ifndef EXPERIMENTAL_USERS_BGALEHOUSE_GRR_CPP_CLIENT_COMPRESSION_H_
#define EXPERIMENTAL_USERS_BGALEHOUSE_GRR_CPP_CLIENT_COMPRESSION_H_

#include <string>

namespace grr {
class ZLib {
 public:
  static string Inflate(const string& input);
  static string Deflate(const string& input);
};
}

#endif  // EXPERIMENTAL_USERS_BGALEHOUSE_GRR_CPP_CLIENT_COMPRESSION_H_
