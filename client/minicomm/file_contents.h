#ifndef GRR_CLIENT_MINICOMM_FILE_CONTENTS_H_
#define GRR_CLIENT_MINICOMM_FILE_CONTENTS_H_

#include <iterator>
#include <memory>

#include "grr/client/minicomm/file_operations.h"

namespace grr {

class FileContentsIterator;

// Provides read only random access to the contends of fd. The observed size
// is fixed during the constructor. If the file is truncated after construction,
// the missing bytes will be seen as having zero value.
class FileContents {
 public:
  explicit FileContents(OpenedPath* fd)
      : error_(""),
        fd_(fd),
        blocks_(fd_->size() / kBlockSize +
                ((fd_->size() % kBlockSize) ? 1 : 0)),
        recent_block_index_(0) {}

  // These iterators, and their derivatives are use *this for backing and are
  // unsafe once *this is deleted.
  FileContentsIterator begin();
  FileContentsIterator end();

 private:
  // Used to read the file:
  std::string error_;
  OpenedPath* const fd_;

  // A power of 2. Expressions like n/kBlockSize and n%kBlockSize will be
  // optimized into bit shifts and masks.
  static constexpr size_t kBlockSize = 64 * 1024;
  struct Block {
    char data[kBlockSize];
  };

  // Find or load a block. Will return nullptr if index is >= blocks_.size().
  std::shared_ptr<Block> GetBlock(int index);

  // A directory of blocks. Pre-allocated to store a (possibly empty) reference
  // to every block.
  std::vector<std::weak_ptr<Block>> blocks_;

  // If we have an iterator to a block, it will stay loaded. In addition we
  // always keep the last 4 blocks that we've loaded. This is to minimize the
  // chance of thrashing if an iterator moves back and forth repeatedly across a
  // block boundary.
  static constexpr int kNumRecentBlocks = 4;
  unsigned int recent_block_index_;
  std::shared_ptr<Block> recent_blocks_[kNumRecentBlocks];

  friend class FileContentsIterator;
};

// Random access iterator over the contents of a file. This is meant an
// alternative to a pointer to a memmapped file with the following two
// advantages:
// 1) Does not crash if the file is truncated after creation.
// 2) Can read large files on 32 bit systems.
class FileContentsIterator
    : public std::iterator<std::random_access_iterator_tag, char, int64> {
 private:
 public:
  FileContentsIterator(difference_type offset, FileContents* contents)
      : contents_(contents) {
    GOOGLE_DCHECK(offset <= contents->fd_->size());
    block_offset_ = offset % kBlockSize;
    block_index_ = offset / kBlockSize;
    data_ = contents->GetBlock(block_index_);
  }
  FileContentsIterator() : contents_(nullptr) {}

  inline difference_type FileOffset() const {
    return block_offset_ + block_index_ * FileContents::kBlockSize;
  }

  FileContentsIterator(const FileContentsIterator&) = default;
  FileContentsIterator(FileContentsIterator&&) = default;
  FileContentsIterator& operator=(const FileContentsIterator&) = default;
  FileContentsIterator& operator=(FileContentsIterator&&) = default;

  FileContentsIterator& operator++() {
    if (block_offset_ < kBlockSize - 1) {
      block_offset_ += 1;
      return *this;
    }
    block_offset_ = 0;
    block_index_ += 1;
    data_ = contents_->GetBlock(block_index_);
    return *this;
  }

  FileContentsIterator operator++(int) {
    FileContentsIterator r = *this;
    ++(*this);
    return r;
  }

  FileContentsIterator& operator+=(difference_type n) {
    if (n == 0) {
      return *this;
    }
    difference_type n_offset = block_offset_ + n;
    if (IsValidBlockOffset(n_offset)) {
      block_offset_ = n_offset;
      return *this;
    }
    const difference_type current_offset = FileOffset();
    GOOGLE_DCHECK(n > 0 || -n <= current_offset);
    const difference_type new_offset = current_offset + n;
    *this = FileContentsIterator(new_offset, contents_);
    return *this;
  }

  FileContentsIterator& operator-=(difference_type n) { return * this += -n; }

  FileContentsIterator operator+(difference_type n) const {
    FileContentsIterator r(*this);
    r += n;
    return r;
  }

  friend FileContentsIterator operator+(difference_type n,
                                        const FileContentsIterator& rhs) {
    return rhs + n;
  }

  FileContentsIterator operator-(difference_type n) {
    FileContentsIterator r(*this);
    r += -n;
    return r;
  }

  difference_type operator-(const FileContentsIterator& rhs) {
    return FileOffset() - rhs.FileOffset();
  }

  FileContentsIterator& operator--() {
    if (block_offset_ > 0) {
      block_offset_ -= 1;
      return *this;
    }
    GOOGLE_DCHECK(block_index_ > 0);
    block_offset_ = kBlockSize - 1;
    block_index_ -= 1;
    data_ = contents_->GetBlock(block_index_);
    return *this;
  }

  FileContentsIterator operator--(int) {
    FileContentsIterator r = *this;
    --(*this);
    return r;
  }

  char operator*() const {
    GOOGLE_DCHECK(IsValidBlockOffset(block_offset_));
    GOOGLE_DCHECK(data_ != nullptr);
    return data_->data[block_offset_];
  }

  char operator[](difference_type n) const {
    const difference_type n_offset = block_offset_ + n;
    if (IsValidBlockOffset(n_offset)) {
      return data_->data[n_offset];
    }
    return *FileContentsIterator(FileOffset() + n, contents_);
  }

  bool operator==(const FileContentsIterator& rhs) const {
    GOOGLE_DCHECK(contents_ == rhs.contents_);
    return block_offset_ == rhs.block_offset_ &&
           block_index_ == rhs.block_index_;
  }

  bool operator!=(const FileContentsIterator& rhs) const {
    GOOGLE_DCHECK(contents_ == rhs.contents_);
    return block_offset_ != rhs.block_offset_ ||
           block_index_ != rhs.block_index_;
  }

  bool operator<(const FileContentsIterator& rhs) const {
    GOOGLE_DCHECK(contents_ == rhs.contents_);
    return block_index_ < rhs.block_index_ ||
           (block_index_ == rhs.block_index_ &&
            block_offset_ < rhs.block_offset_);
  }

  bool operator>(const FileContentsIterator& rhs) const { return rhs < *this; }

  bool operator<=(const FileContentsIterator& rhs) const {
    return block_index_ < rhs.block_index_ ||
           (block_index_ == rhs.block_index_ &&
            block_offset_ <= rhs.block_offset_);
  }

  bool operator>=(const FileContentsIterator& rhs) const {
    return rhs <= *this;
  }

  const char* operator->() const {
    GOOGLE_DCHECK(IsValidBlockOffset(block_offset_));
    GOOGLE_DCHECK(data_ != nullptr);
    return &data_->data[block_offset_];
  }

 private:
  static constexpr size_t kBlockSize = FileContents::kBlockSize;
  typedef FileContents::Block Block;

  static inline bool IsValidBlockOffset(difference_type offset) {
    return offset >= 0 && offset < kBlockSize;
  }

  int block_offset_;
  int block_index_;
  std::shared_ptr<Block> data_;
  FileContents* contents_;
};

inline FileContentsIterator FileContents::begin() {
  return FileContentsIterator(0, this);
}

inline FileContentsIterator FileContents::end() {
  return FileContentsIterator(fd_->size(), this);
}
}  // namespace grr
#endif  // GRR_CLIENT_MINICOMM_FILE_CONTENTS_H_
