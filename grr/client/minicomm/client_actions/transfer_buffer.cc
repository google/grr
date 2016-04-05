#include "grr/client/minicomm/client_actions/transfer_buffer.h"

#include "grr/client/minicomm/compression.h"
#include "grr/client/minicomm/crypto.h"
#include "grr/client/minicomm/paths.h"

namespace grr {
namespace actions {
void TransferBuffer::ProcessRequest(ActionContext* context) {
  BufferReference req;
  if (!context->PopulateArgs(&req)) {
    return;
  }
  // Don't transfer if this is really a HashBuffer request.
  const bool transfer = context->Message().name() == "TransferBuffer";

  std::string error;
  auto file = Paths::NormalizeAndOpen(req.mutable_pathspec(), &error);
  if (file == nullptr) {
    context->SetError(error);
    return;
  }
  if (req.offset() > 0) {
    if (!file->Seek(req.offset(), &error)) {
      context->SetError(error);
      return;
    }
  }

  Digest sha256(Digest::Type::SHA256);
  std::unique_ptr<ZDeflate> compressed(transfer ? new ZDeflate : nullptr);

  char buff[64 * 1024];
  size_t bytes_remaining = req.length();
  size_t bytes_read = (size_t)-1;

  while (bytes_read != 0 && bytes_remaining > 0) {
    if (!file->Read(buff, bytes_remaining, &bytes_read, &error)) {
      context->SetError(error);
      return;
    }
    sha256.Update(buff, bytes_read);
    if (transfer) {
      compressed->Update(buff, bytes_read);
    }
    bytes_remaining -= bytes_read;
  }
  if (transfer) {
    GrrMessage blob_message;
    {
      DataBlob blob;
      blob.set_compression(DataBlob::ZCOMPRESSION);
      *blob.mutable_data() = compressed->Final();
      blob.SerializeToString(blob_message.mutable_args());
    }
    blob_message.set_args_rdf_name("DataBlob");
    blob_message.set_session_id("F:TransferStore");
    context->SendMessage(blob_message);
  }
  BufferReference res;
  res.set_offset(req.offset());
  res.set_length(req.length() - bytes_remaining);
  res.set_data(sha256.Final());
  context->SendResponse(res, GrrMessage::MESSAGE);
}
}  // namespace actions
}  // namespace grr
