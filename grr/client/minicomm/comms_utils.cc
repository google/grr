#include "comms_utils.h"

#include <endian.h>
#include <stdint.h>
#include <algorithm>

#include "google/protobuf/repeated_field.h"

#include "grr/client/minicomm/base.h"
#include "grr/client/minicomm/compression.h"

namespace grr {
// *** MessageBuilder ***
void MessageBuilder::InitiateEnrollment(ClientConfig* config,
                                        MessageQueue* outbox) {
  CertificateSR csr;
  csr.SetSubject(config->ClientId());
  RSAKey my_key(config->key());

  if (my_key.get() == nullptr) {
    config->ResetKey();

    my_key = config->key();
  }

  csr.SetPublicKey(&my_key);
  csr.Sign(&my_key);

  GrrMessage enrollment_message;
  enrollment_message.set_session_id("aff4:/flows/CA:Enrol");

  ::Certificate cert_pb;
  cert_pb.set_type(::Certificate::CSR);
  cert_pb.set_pem(csr.ToStringPEM());
  enrollment_message.set_args(cert_pb.SerializeAsString());
  enrollment_message.set_args_rdf_name("Certificate");
  enrollment_message.set_source(config->ClientId());
  outbox->AddPriorityMessage(enrollment_message);
}

// *** SecureSession ***

namespace {
std::string ComputeHMAC(const std::string& key,
                        const ClientCommunication& input) {
  Sha1HMAC hmac(key);
  hmac.Update(input.encrypted());
  hmac.Update(input.encrypted_cipher());
  hmac.Update(input.encrypted_cipher_metadata());
  hmac.Update(input.packet_iv());
  // Need the bytes for api_version as a 32 bit little endian value.
  uint32_t converted_version = htole32(input.api_version());
  std::string version_string(reinterpret_cast<char*>(&converted_version), 4);
  hmac.Update(version_string);
  return hmac.Final();
}
}  // namespace

SecureSession::SecureSession(const std::string& client_id, RSAKey* our_key,
                             std::unique_ptr<Certificate> target_cert)
    : our_key_(our_key), target_cert_(std::move(target_cert)) {
  CipherProperties properties;
  properties.set_name("aes_128_cbc");
  properties.set_key(CryptoRand::RandBytes(16));
  properties.set_metadata_iv(CryptoRand::RandBytes(16));
  properties.set_hmac_key(CryptoRand::RandBytes(16));
  properties.set_hmac_type(CipherProperties::FULL_HMAC);
  std::string serialized_properties = properties.SerializeAsString();
  encrypted_cipher_properties_ = target_cert_->Encrypt(serialized_properties);

  session_key_ = properties.key();
  hmac_key_ = properties.hmac_key();

  CipherMetadata metadata;
  metadata.set_signature(our_key_->SignSha256(serialized_properties));
  metadata.set_source(client_id);

  encrypted_cipher_metadata_ = AES128CBCCipher::Encrypt(
      properties.key(), properties.metadata_iv(), metadata.SerializeAsString());
}

ClientCommunication SecureSession::EncodeMessages(
    const std::vector<GrrMessage>& messages, int64 nonce) {
  ClientCommunication result;
  result.set_encrypted_cipher(encrypted_cipher_properties_);
  result.set_encrypted_cipher_metadata(encrypted_cipher_metadata_);
  result.set_packet_iv(CryptoRand::RandBytes(16));
  result.set_api_version(3);

  SignedMessageList signed_list = PackMessages(messages);
  signed_list.set_timestamp(nonce);
  result.set_encrypted(AES128CBCCipher::Encrypt(
      session_key_, result.packet_iv(), signed_list.SerializeAsString()));

  result.set_full_hmac(ComputeHMAC(hmac_key_, result));
  return result;
}

SignedMessageList SecureSession::PackMessages(
    const std::vector<GrrMessage>& messages) {
  MessageList list;
  *list.mutable_job() = google::protobuf::RepeatedPtrField<GrrMessage>(
      messages.begin(), messages.end());
  SignedMessageList result;
  std::string serialized_result = list.SerializeAsString();
  std::string compressed_result = ZLib::Deflate(serialized_result);
  if (serialized_result.length() <= compressed_result.length()) {
    result.mutable_message_list()->swap(serialized_result);
  } else {
    result.mutable_message_list()->swap(compressed_result);
    result.set_compression(SignedMessageList::ZCOMPRESSION);
  }
  return result;
}

bool SecureSession::DecodeMessages(const ClientCommunication& input,
                                   std::vector<GrrMessage>* output,
                                   int64 nonce) {
  const std::string serialized_cipher =
      our_key_->Decrypt(input.encrypted_cipher());
  if (serialized_cipher.empty()) {
    GOOGLE_LOG(ERROR) << "Could not decrypt cipher.";
    return false;
  }
  CipherProperties cipher_props;
  if (!cipher_props.ParseFromString(serialized_cipher)) {
    GOOGLE_LOG(ERROR) << "Could not parse cipher.";
    return false;
  }

  const std::string expected_hmac = ComputeHMAC(cipher_props.hmac_key(), input);
  if (expected_hmac != input.full_hmac()) {
    GOOGLE_LOG(ERROR) << "HMAC mismatch.";
    return false;
  }

  std::string decrypted_packet = AES128CBCCipher::Decrypt(
      cipher_props.key(), input.packet_iv(), input.encrypted());
  if (decrypted_packet.empty()) {
    GOOGLE_LOG(ERROR) << "Could not decrypt packet.";
    return false;
  }
  SignedMessageList s_message_list;
  if (!s_message_list.ParseFromString(decrypted_packet)) {
    GOOGLE_LOG(ERROR) << "Could not parse packet:" << decrypted_packet;
    GOOGLE_LOG(ERROR) << "Found:" << s_message_list.DebugString();
    return false;
  }
  if (s_message_list.timestamp() != nonce) {
    GOOGLE_LOG(ERROR) << "Nonce mismatch.";
    return false;
  }

  bool parse_result;
  MessageList message_list;
  switch (s_message_list.compression()) {
    case SignedMessageList::UNCOMPRESSED:
      parse_result =
          message_list.ParseFromString(s_message_list.message_list());
      break;
    case SignedMessageList::ZCOMPRESSION:
      parse_result = message_list.ParseFromString(
          ZLib::Inflate(s_message_list.message_list()));
      break;
    default:
      GOOGLE_LOG(ERROR) << "Unknown compression option:"
                        << s_message_list.compression();
  }
  if (!parse_result) {
    GOOGLE_LOG(ERROR) << "Could not parse message list.";
    return false;
  }
  for (const auto& message : message_list.job()) {
    output->emplace_back(message);
  }
  return true;
}

uint64 NonceGenerator::Generate() {
  const auto now = std::chrono::high_resolution_clock::now();
  uint64 now_usec = std::chrono::duration_cast<std::chrono::microseconds>(
      now.time_since_epoch())
      .count();
  uint64 result = std::max(last_nonce_ + 1, now_usec);
  last_nonce_ = result;
  return result;
}
}  // namespace grr
