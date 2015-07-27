#include "grr/client/minicomm/client_actions/fingerprint_file.h"

#include "grr/client/minicomm/crypto.h"
#include "grr/client/minicomm/paths.h"

namespace grr {
namespace actions {
void FingerprintFile::ProcessRequest(ActionContext* context) {
  FingerprintRequest req;
  if (!context->PopulateArgs(&req)) {
    return;
  }

  std::string error;
  auto f = Paths::NormalizeAndOpen(req.mutable_pathspec(), &error);
  if (f == nullptr) {
    context->SetError(error);
    return;
  }

  Digest md5(Digest::Type::MD5);
  Digest sha1(Digest::Type::SHA1);
  Digest sha256(Digest::Type::SHA256);

  const size_t max_size = req.max_filesize();
  size_t total_bytes_read = 0;
  size_t bytes_read = (size_t)-1;

  char buffer[64 * 1024];
  while (bytes_read != 0 && total_bytes_read < max_size) {
    if (!f->Read(buffer, max_size - total_bytes_read, &bytes_read, &error)) {
      context->SetError(error);
      return;
    }
    md5.Update(buffer, bytes_read);
    sha1.Update(buffer, bytes_read);
    sha256.Update(buffer, bytes_read);

    total_bytes_read += bytes_read;
  }

  FingerprintResponse res;
  *res.mutable_pathspec() = req.pathspec();
  res.set_bytes_read(total_bytes_read);
  res.mutable_hash()->set_md5(md5.Final());
  res.mutable_hash()->set_sha1(sha1.Final());
  res.mutable_hash()->set_sha256(sha256.Final());

  context->SendResponse(res, GrrMessage::MESSAGE);
}
}  // namespace actions
}  // namespace grr
