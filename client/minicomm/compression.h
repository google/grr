#ifndef GRR_CLIENT_MINICOMM_COMPRESSION_H_
#define GRR_CLIENT_MINICOMM_COMPRESSION_H_

#include <string>

namespace grr {
class ZLib {
 public:
  static std::string Inflate(const std::string& input);
  static std::string Deflate(const std::string& input);
};
}

#endif  // GRR_CLIENT_MINICOMM_COMPRESSION_H_
