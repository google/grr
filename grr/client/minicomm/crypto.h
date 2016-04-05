#ifndef GRR_CLIENT_MINICOMM_CRYPTO_H_
#define GRR_CLIENT_MINICOMM_CRYPTO_H_

#include <string>

#include "openssl/hmac.h"
#include "openssl/md5.h"
#include "openssl/pem.h"
#include "openssl/rsa.h"
#include "openssl/x509.h"

#include "grr/client/minicomm/base.h"
#include "grr/client/minicomm/scoped_ptr_ssl.h"

// Thin C++ wrappers around openssl data structures, providing the limited
// functionality required by grr in a C++ friendly format.

namespace grr {

// Incremental digest computation.

class Digest {
 public:
  // The types of hash that we support.
  enum class Type { MD5, SHA1, SHA256 };

  // Convenience method to compute a hash in a single step.
  static std::string Hash(Type t, const std::string& input);

  // Create an incremental digest state of type t.
  explicit Digest(Type t);
  ~Digest();

  // Stream limit bytes into the hash from buffer.
  template <size_t size>
  void Update(const char(&buffer)[size], size_t limit) {
    UpdateInternal(buffer, std::min(size, limit));
  }

  // Stream input into the hash.
  void Update(const std::string& input);

  // Return the hash of everything added by Update().
  std::string Final();

 private:
  void UpdateInternal(const char* buffer, size_t limit);
  EVP_MD_CTX ctx_;
};

// Incremental HMAC computation.
class Sha1HMAC {
 public:
  explicit Sha1HMAC(const std::string& key);
  ~Sha1HMAC();
  void Update(const std::string& input);
  std::string Final();

 private:
  HMAC_CTX ctx_;
};

// Represents a client's RSA key.
class RSAKey {
 public:
  RSAKey() {}
  ~RSAKey() {}

  // Initialize the key with a newly generated RSA keypair. Returns true on
  // success.
  bool Generate();

  // Initialize the key from a PEM format string. Returns true on success.
  bool FromPEM(const std::string& pem);

  // Attempt to produce a PEM string containing the current key. Returns the
  // empty string on failure.
  std::string ToStringPEM() const;

  // Returns the value n of the public key, in the big endian binary format
  // produced by the openssl bn2mpi function.
  std::string PublicKeyN() const;

  // Produce a signature for the sha256 digest of input.
  std::string SignSha256(const std::string& input);

  // Decrypt input using our private key.
  std::string Decrypt(const std::string& input);

  // For low level access to the underlying openssl struct. Does not pass
  // ownership.  Returns NULL if we do not have a valid key.
  RSA* get() { return key_.get(); }

  RSAKey(RSAKey&& other) = default;
  RSAKey(const RSAKey& other);
  void operator=(const RSAKey& other);

 private:
  scoped_ptr_openssl_void<RSA, RSA_free> key_;
};

// Represents a X509 certificate.
class Certificate {
 public:
  // Creates an unsigned certificate containing an RSA public key. Meant for
  // testing.
  explicit Certificate(RSAKey& key);
  Certificate() {}
  ~Certificate() {}

  // Initialize the cert from a PEM format string. Returns true on success.
  bool FromPEM(const std::string& pem);

  // Attempt to produce a PEM string containing the current cert. Returns the
  // empty string on failure.
  std::string ToStringPEM() const;

  // Verify that candidate has been signed by this. Returns true if verification
  // succedes.
  bool Verify(const Certificate& candidate);

  // Encrypt input using the public key embedded in this cert.
  // This directly uses the RSA math and allows inputs within the group size.
  std::string Encrypt(const std::string& input);

  // Return the serial number embedded in this certificate.
  int GetSerialNumber();

  // Verify the signature of a sha256 digest of the input string.
  bool VerifySha256(const std::string& input);

  // For low level access to the underlying openssl struct. Does not pass
  // ownership.
  X509* get() { return cert_.get(); }

  Certificate(Certificate&& other) = default;
  Certificate(const Certificate& other);
  void operator=(const Certificate& other) = delete;

 private:
  scoped_ptr_openssl_void<X509, X509_free> cert_;
};

// Represents a X509 certificate signing request. Used by the client to request
// that the server sign the client's key.
class CertificateSR {
 public:
  CertificateSR();

  // Set the request's public key from a client key.
  bool SetPublicKey(RSAKey* key);

  // Set the subject name associated with the CSR.
  bool SetSubject(const std::string& subject);

  // Sign the request with the client key.
  bool Sign(RSAKey* key);

  // Attempt to produce a PEM string containing the current cert. Returns the
  // empty string on failure.
  std::string ToStringPEM() const;

  // For low level access to the underlying openssl struct. Does not pass
  // ownership.
  X509_REQ* get() { return request_.get(); }

  CertificateSR(CertificateSR&& other) = default;
  CertificateSR(const CertificateSR& other) = delete;
  void operator=(const CertificateSR& other) = delete;

 private:
  scoped_ptr_openssl_void<X509_REQ, X509_REQ_free> request_;
};

class AES128CBCCipher {
 public:
  static std::string Encrypt(const std::string& key, const std::string& iv,
                             const std::string& input);
  static std::string Decrypt(const std::string& key, const std::string& iv,
                             const std::string& input);

 private:
  AES128CBCCipher();
};

class CryptoRand {
 public:
  static std::string RandBytes(int num_bytes);
  static uint64 RandInt64();
};

}  // namespace grr

#endif  // GRR_CLIENT_MINICOMM_CRYPTO_H_
