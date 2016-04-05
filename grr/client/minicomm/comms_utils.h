#ifndef GRR_CLIENT_MINICOMM_COMMS_UTILS_H_
#define GRR_CLIENT_MINICOMM_COMMS_UTILS_H_

#include <memory>
#include <string>
#include <vector>

#include "grr/proto/jobs.pb.h"
#include "grr/client/minicomm/base.h"
#include "grr/client/minicomm/config.h"
#include "grr/client/minicomm/crypto.h"
#include "grr/client/minicomm/message_queue.h"

namespace grr {

class MessageBuilder {
 public:
  static void InitiateEnrollment(ClientConfig* config, MessageQueue* outbox);
};

class NonceGenerator {
 public:
  NonceGenerator() : last_nonce_(0) {}
  uint64 Generate();

 private:
  uint64 last_nonce_;
};

class SecureSession {
 public:
  SecureSession(const std::string& client_id, RSAKey* our_key,
                std::unique_ptr<Certificate> target_cert);

  // Encrypts, signs and packages a set of messages into a ClientCommunitation.
  ClientCommunication EncodeMessages(const std::vector<GrrMessage>& messages,
                                     int64 nonce);

  // Attempt to decode and verify a ClientCommunication created for us.
  // Returns true on success. GrrMessage records are appended to output.
  bool DecodeMessages(const ClientCommunication& messages,
                      std::vector<GrrMessage>* output, int64 nonce);

 private:
  SignedMessageList PackMessages(const std::vector<GrrMessage>& messages);

  std::string encrypted_cipher_properties_;
  std::string encrypted_cipher_metadata_;

  std::string session_key_;
  std::string hmac_key_;

  // External components.
  RSAKey* our_key_;
  std::unique_ptr<Certificate> target_cert_;
};
}  // namespace grr

#endif  // GRR_CLIENT_MINICOMM_COMMS_UTILS_H_
