#include "compression.h"

#include <algorithm>
#include <memory>
#include <vector>

#include "base.h"
#include "zlib.h"

namespace grr {
namespace {
z_stream MakeZS(const std::string& input) {
  z_stream zs;
  zs.zalloc = Z_NULL;
  zs.zfree = Z_NULL;
  zs.opaque = Z_NULL;

  zs.next_in = const_cast<unsigned char*>(
      reinterpret_cast<const unsigned char*>(input.data()));
  zs.avail_in = input.length();
  return zs;
}
}  // namespace

std::string ZLib::Inflate(const std::string& input) {
  const auto block_size = std::max(input.size(), 1024UL);
  std::vector<std::unique_ptr<unsigned char[]>> output_blocks;
  output_blocks.emplace_back(new unsigned char[block_size]());

  z_stream zs = MakeZS(input);
  inflateInit(&zs);
  zs.next_out = output_blocks.back().get();
  zs.avail_out = block_size;
  int result;
  while ((result = inflate(&zs, Z_SYNC_FLUSH)) == Z_OK) {
    if (zs.avail_out != 0) {
      GOOGLE_LOG(ERROR) << "ZLIB didn't fill block.";
      return "";
    }
    output_blocks.emplace_back(new unsigned char[block_size]());
    zs.next_out = output_blocks.back().get();
    zs.avail_out = block_size;
  }
  if (result != Z_STREAM_END) {
    GOOGLE_LOG(ERROR) << "Unexpected ZLIB result:" << result;
    return "";
  }
  std::string r;
  r.reserve(zs.total_out);
  for (int i = 0; i < output_blocks.size() - 1; i++) {
    r.append(reinterpret_cast<char*>(output_blocks[i].get()), block_size);
  }
  r.append(reinterpret_cast<char*>(output_blocks.back().get()),
           block_size - zs.avail_out);
  inflateEnd(&zs);
  return r;
}

std::string ZLib::Deflate(const std::string& input) {
  z_stream zs = MakeZS(input);

  deflateInit(&zs, Z_DEFAULT_COMPRESSION);
  const int max_out = deflateBound(&zs, input.length());
  std::unique_ptr<unsigned char[]> output(new unsigned char[max_out]());
  zs.next_out = output.get();
  zs.avail_out = max_out;
  deflate(&zs, Z_FINISH);
  deflateEnd(&zs);
  return std::string(reinterpret_cast<char*>(output.get()), zs.total_out);
}
}  // namespace grr
