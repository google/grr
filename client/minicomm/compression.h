#ifndef GRR_CLIENT_MINICOMM_COMPRESSION_H_
#define GRR_CLIENT_MINICOMM_COMPRESSION_H_

#include <memory>
#include <string>
#include <vector>

#include "zlib.h"

namespace grr {
class ZLib {
 public:
  static std::string Inflate(const std::string& input);
  static std::string Deflate(const std::string& input);
};

// A class to perform an incremental deflate (compression) a stream of input
// blocks.
class ZDeflate {
 public:
  ZDeflate();
  ~ZDeflate();

  // Add up to limit bytes from buffer to the internal stream.
  template <size_t size>
  void Update(const char(&buffer)[size], size_t limit) {
    UpdateInternal(buffer, std::min(size, limit));
  }

  // Return the internal stream in compressed format.
  std::string Final();

 private:
  static constexpr size_t kBlockSize = 1024 * 64;

  void UpdateInternal(const char* buffer, size_t limit);

  // The blocks of output.
  std::vector<std::unique_ptr<unsigned char[]>> output_blocks_;

  z_stream zs_;
};
}  // namespace grr

#endif  // GRR_CLIENT_MINICOMM_COMPRESSION_H_
