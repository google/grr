#ifndef EXPERIMENTAL_USERS_BGALEHOUSE_GRR_CPP_CLIENT_COMMS_UTILS_H_
#define EXPERIMENTAL_USERS_BGALEHOUSE_GRR_CPP_CLIENT_COMMS_UTILS_H_

#include <memory>
#include <string>
#include <vector>

#include "../../proto/jobs.pb.h"
#include "base.h"
#include "config.h"
#include "crypto.h"
#include "message_queue.h"

namespace grr {

class MessageBuilder {
 public:
  typedef google3::ops::security::grr::GrrMessage Message;
  static void InitiateEnrollment(ClientConfig* config, MessageQueue* outbox);
};

class SecureSession {
 public:
  typedef google3::ops::security::grr::GrrMessage Message;
  typedef google3::ops::security::grr::ClientCommunication ClientCommunication;
  typedef google3::ops::security::grr::SignedMessageList SignedMessageList;

  SecureSession(const string& client_id, RSAKey* our_key,
                std::unique_ptr<Certificate> target_cert);

  // Encrypts, signs and packages a set of messages into a ClientCommunitation.
  ClientCommunication EncodeMessages(const vector<Message>& messages,
                                     int64 nonce);

  // Attempt to decode and verify a ClientCommunication created for us.
  // Returns true on success. GrrMessage records are appended to output.
  bool DecodeMessages(const ClientCommunication& messages,
                      vector<Message>* output,  int64 nonce);

 private:
  SignedMessageList PackMessages(const vector<Message>& messages);

  string encrypted_cipher_properties_;
  string encrypted_cipher_metadata_;

  string session_key_;
  string hmac_key_;

  // External components.
  RSAKey* our_key_;
  std::unique_ptr<Certificate> target_cert_;
};
}  // namespace grr

#endif  // EXPERIMENTAL_USERS_BGALEHOUSE_GRR_CPP_CLIENT_COMMS_UTILS_H_
