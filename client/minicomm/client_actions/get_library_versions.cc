#include "grr/client/minicomm/client_actions/get_library_versions.h"

#include "curl/curl.h"
#include "openssl/crypto.h"

#include "grr/proto/jobs.pb.h"
#include "google/protobuf/stubs/common.h"

namespace grr {
namespace actions {
namespace {
void AddKeyValue(const std::string& key, const std::string& value, Dict* dict) {
  KeyValue* kv = dict->add_dat();
  kv->mutable_k()->set_string(key);
  kv->mutable_v()->set_string(value);
}
}
void GetLibraryVersions::ProcessRequest(ActionContext* context) {
  Dict res;
  AddKeyValue("openssl", SSLeay_version(SSLEAY_VERSION), &res);
  AddKeyValue("curl", curl_version(), &res);
  AddKeyValue(
      "protobuf",
      google::protobuf::internal::VersionString(GOOGLE_PROTOBUF_VERSION), &res);
  context->SendResponse(res, GrrMessage::MESSAGE);
}
}  // namespace actions
}  // namespace grr
