#ifndef EXPERIMENTAL_USERS_BGALEHOUSE_GRR_CPP_CLIENT_CRYPTO_H_
#define EXPERIMENTAL_USERS_BGALEHOUSE_GRR_CPP_CLIENT_CRYPTO_H_

#include <string>

#include "openssl/hmac.h"
#include "openssl/pem.h"
#include "openssl/rsa.h"
#include "openssl/x509.h"
#include "scoped_ptr_ssl.h"

// Thin C++ wrappers around openssl data structures, providing the limited
// functionality required by grr in a C++ friendly format.

namespace grr {

// Hashing/digest functions.
class Digest {
 public:
  static string Sha256(const string& input);
};

// Incremental HMAC computation.
class Sha1HMAC {
 public:
  Sha1HMAC(const string& key);
  ~Sha1HMAC();
  void Update(const string& input);
  string Final();

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
  bool FromPEM(const string& pem);

  // Attempt to produce a PEM string containing the current key. Returns the
  // empty string on failure.
  string ToStringPEM() const;

  // Returns the value n of the public key, in the big endian binary format
  // produced by the openssl bn2mpi function.
  string PublicKeyN() const;

  // Produce a signature for the sha256 digest of input.
  string SignSha256(const string& input);

  // Decrypt input using our private key.
  string Decrypt(const string& input);

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
  Certificate(RSAKey& key);
  Certificate() {}
  ~Certificate() {}

  // Initialize the cert from a PEM format string. Returns true on success.
  bool FromPEM(const string& pem);

  // Attempt to produce a PEM string containing the current cert. Returns the
  // empty string on failure.
  string ToStringPEM() const;

  // Verify that candidate has been signed by this. Returns true if verification
  // succedes.
  bool Verify(const Certificate& candidate);

  // Encrypt input using the public key embedded in this cert.
  // This directly uses the RSA math and allows inputs within the group size.
  string Encrypt(const string& input);

  // Return the serial number embedded in this certificate.
  int GetSerialNumber();

  // Verify the signature of a sha256 digest of the input string.
  bool VerifySha256(const string& input);

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
  bool SetSubject(const string& subject);

  // Sign the request with the client key.
  bool Sign(RSAKey* key);

  // Attempt to produce a PEM string containing the current cert. Returns the
  // empty string on failure.
  string ToStringPEM() const;

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
  static string Encrypt(const string& key, const string& iv,
                        const string& input);
  static string Decrypt(const string& key, const string& iv,
                        const string& input);

 private:
  AES128CBCCipher();
};

class CryptoRand {
 public:
  static string RandBytes(int num_bytes);
  static uint64 RandInt64();
};

}  // namespace grr

#endif  // EXPERIMENTAL_USERS_BGALEHOUSE_GRR_CPP_CLIENT_CRYPTO_H_
