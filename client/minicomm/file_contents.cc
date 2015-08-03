#include "grr/client/minicomm/file_contents.h"

namespace grr {

std::shared_ptr<FileContents::Block> FileContents::GetBlock(int index) {
  std::shared_ptr<Block> r;
  if (index < 0 || index >= blocks_.size()) {
    return r;
  }
  r = blocks_[index].lock();
  if (r != nullptr) {
    return std::move(r);
  }
  r.reset(new Block());
  fd_->Seek(static_cast<uint64>(index) * static_cast<uint64>(kBlockSize),
            &error_);
  size_t bytes_read = 0;
  fd_->Read(r->data, fd_->size() - index * kBlockSize, &bytes_read, &error_);
  if (bytes_read < kBlockSize) {
    memset(&r->data[bytes_read], '\0', kBlockSize - bytes_read);
  }
  blocks_[index] = r;
  recent_blocks_[recent_block_index_++ % kNumRecentBlocks] = r;
  return std::move(r);
}

}  // namespace grr
