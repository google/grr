#include "grr/client/minicomm/crypto.h"

#include <stddef.h>
#include <memory>

#include "openssl/bio.h"
#include "openssl/evp.h"
#include "openssl/pem.h"
#include "openssl/rand.h"
#include "openssl/sha.h"

namespace grr {
namespace {
inline std::string BIOToString(BIO* bio) {
  char* data;
  const long len = BIO_get_mem_data(bio, &data);
  if (len <= 0 || !data) {
    return "";
  }
  return std::string(data, len);
}

inline const unsigned char* StringToBytes(const std::string& input) {
  return reinterpret_cast<const unsigned char*>(input.data());
}
}  // namespace

// *** Digest ***
Digest::Digest(Digest::Type t) {
  const EVP_MD* type = nullptr;
  switch (t) {
    case Type::MD5:
      type = EVP_md5();
      break;
    case Type::SHA1:
      type = EVP_sha1();
      break;
    case Type::SHA256:
      type = EVP_sha256();
      break;
    default:
      GOOGLE_LOG(FATAL) << "Unknown digest type:" << int(t);
  }
  EVP_MD_CTX_init(&ctx_);
  if (!EVP_DigestInit_ex(&ctx_, type, nullptr)) {
    GOOGLE_LOG(FATAL) << "Unable to initialize digest context.";
  }
}

void Digest::UpdateInternal(const char* buffer, size_t limit) {
  EVP_DigestUpdate(&ctx_, reinterpret_cast<const unsigned char*>(buffer),
                   limit);
}

void Digest::Update(const std::string& input) {
  UpdateInternal(input.data(), input.length());
}

std::string Digest::Final() {
  unsigned int digest_size;
  std::unique_ptr<unsigned char[]> buf(
      new unsigned char[EVP_MD_CTX_size(&ctx_)]);
  EVP_DigestFinal_ex(&ctx_, buf.get(), &digest_size);
  return std::string(reinterpret_cast<char*>(buf.get()), digest_size);
}

Digest::~Digest() { EVP_MD_CTX_cleanup(&ctx_); }

std::string Digest::Hash(Digest::Type t, const std::string& input) {
  Digest d(t);
  d.Update(input);
  return d.Final();
}

// *** Sha1HMAC ***
Sha1HMAC::Sha1HMAC(const std::string& key) {
  HMAC_CTX_init(&ctx_);
  HMAC_Init_ex(&ctx_, StringToBytes(key), key.length(), EVP_sha1(), NULL);
}

Sha1HMAC::~Sha1HMAC() { HMAC_CTX_cleanup(&ctx_); }

void Sha1HMAC::Update(const std::string& input) {
  HMAC_Update(&ctx_, StringToBytes(input), input.length());
}

std::string Sha1HMAC::Final() {
  unsigned char digest[EVP_MAX_MD_SIZE];
  unsigned int length;
  HMAC_Final(&ctx_, digest, &length);
  return std::string(reinterpret_cast<char*>(digest), length);
}

// *** RSAKey ***
RSAKey::RSAKey(const RSAKey& other) : key_(other.key_.get()) {
  if (key_.get()) {
    RSA_up_ref(key_.get());
  }
}

void RSAKey::operator=(const RSAKey& other) {
  key_.reset(other.key_.get());

  if (key_.get()) {
    RSA_up_ref(key_.get());
  }
}

bool RSAKey::Generate() {
  key_.reset(RSA_new());
  scoped_ptr_openssl_void<BIGNUM, BN_free> e(BN_new());
  BN_set_word(e.get(), RSA_F4);
  return RSA_generate_key_ex(key_.get(), 2048, e.get(), NULL);
}

bool RSAKey::FromPEM(const std::string& pem) {
  scoped_ptr_openssl_int<BIO, BIO_free> bio(
      BIO_new_mem_buf(const_cast<char*>(pem.data()), pem.size()));
  key_.reset(PEM_read_bio_RSAPrivateKey(bio.get(), NULL, NULL, NULL));
  return key_.get() != nullptr;
}

std::string RSAKey::ToStringPEM() const {
  if (key_.get() == NULL) {
    return "";
  }
  scoped_ptr_openssl_int<BIO, BIO_free> bio(BIO_new(BIO_s_mem()));
  if (!PEM_write_bio_RSAPrivateKey(bio.get(), key_.get(), NULL, NULL, 0, NULL,
                                   NULL)) {
    return "";
  }
  return BIOToString(bio.get());
}

std::string RSAKey::PublicKeyN() const {
  if (key_.get() == NULL || key_.get()->n == NULL) {
    return "";
  }
  BIGNUM* bn = key_.get()->n;
  const int len = BN_bn2mpi(bn, nullptr);
  std::unique_ptr<char[]> buf(new char[len]);
  BN_bn2mpi(bn, reinterpret_cast<unsigned char*>(buf.get()));
  return std::string(buf.get(), len);
}

std::string RSAKey::SignSha256(const std::string& input) {
  if (key_.get() == NULL) {
    return "";
  }
  SHA256_CTX context;
  SHA256_Init(&context);
  SHA256_Update(&context, input.data(), input.length());
  unsigned char digest[SHA256_DIGEST_LENGTH];
  SHA256_Final(digest, &context);
  std::unique_ptr<unsigned char[]> output(
      new unsigned char[RSA_size(key_.get())]);
  unsigned int output_length;
  RSA_sign(NID_sha256, digest, SHA256_DIGEST_LENGTH, output.get(),
           &output_length, key_.get());

  return std::string(reinterpret_cast<const char*>(output.get()),
                     output_length);
}

std::string RSAKey::Decrypt(const std::string& input) {
  std::unique_ptr<unsigned char[]> output(
      new unsigned char[RSA_size(key_.get())]);
  int output_length =
      RSA_private_decrypt(input.length(), StringToBytes(input), output.get(),
                          key_.get(), RSA_PKCS1_OAEP_PADDING);
  if (output_length <= 0) {
    return "";
  }
  return std::string(reinterpret_cast<const char*>(output.get()),
                     output_length);
}

// *** Certificate ***

Certificate::Certificate(RSAKey& key) {
  cert_.reset(X509_new());

  scoped_ptr_openssl_void<EVP_PKEY, EVP_PKEY_free> pkey(EVP_PKEY_new());
  EVP_PKEY_set1_RSA(pkey.get(), key.get());
  X509_set_pubkey(cert_.get(), pkey.get());
}

Certificate::Certificate(const Certificate& other)
    : cert_(X509_dup(other.cert_.get())) {}

bool Certificate::FromPEM(const std::string& pem) {
  scoped_ptr_openssl_int<BIO, BIO_free> bio(
      BIO_new_mem_buf(const_cast<char*>(pem.data()), pem.size()));
  cert_.reset(PEM_read_bio_X509(bio.get(), NULL, NULL, NULL));
  return cert_.get() != NULL;
}

std::string Certificate::ToStringPEM() const {
  if (cert_.get() == NULL) {
    return "";
  }
  scoped_ptr_openssl_int<BIO, BIO_free> bio(BIO_new(BIO_s_mem()));
  if (!PEM_write_bio_X509(bio.get(), cert_.get())) {
    return "";
  }
  return BIOToString(bio.get());
}

bool Certificate::Verify(const Certificate& candidate) {
  if (cert_.get() == NULL || candidate.cert_.get() == NULL) {
    return false;
  }
  scoped_ptr_openssl_void<EVP_PKEY, EVP_PKEY_free> pkey(
      X509_get_pubkey(cert_.get()));
  return X509_verify(candidate.cert_.get(), pkey.get());
}

std::string Certificate::Encrypt(const std::string& input) {
  scoped_ptr_openssl_void<EVP_PKEY, EVP_PKEY_free> pkey(
      X509_get_pubkey(cert_.get()));
  if (!pkey.get()) {
    GOOGLE_LOG(ERROR) << "Unable to make pkey.";
    return "";
  }
  if (EVP_PKEY_type(pkey->type) != EVP_PKEY_RSA) {
    GOOGLE_LOG(ERROR) << "pkey not RSA";
    return "";
  }
  scoped_ptr_openssl_void<RSA, RSA_free> key(EVP_PKEY_get1_RSA(pkey.get()));
  if (!key.get()) {
    GOOGLE_LOG(ERROR) << "Unable to get RSA out of pkey.";
    return "";
  }
  const int rsa_size = RSA_size(key.get());
  if (input.length() >= rsa_size - 41) {
    GOOGLE_LOG(ERROR) << "Input too long for RSA key size.";
    return "";
  }
  std::unique_ptr<unsigned char[]> output(new unsigned char[rsa_size]);
  RSA_public_encrypt(input.length(), StringToBytes(input), output.get(),
                     key.get(), RSA_PKCS1_OAEP_PADDING);
  return std::string(reinterpret_cast<const char*>(output.get()), rsa_size);
}

int Certificate::GetSerialNumber() {
  return ASN1_INTEGER_get(X509_get_serialNumber(cert_.get()));
}

bool Certificate::VerifySha256(const std::string& input) {
  SHA256_CTX context;
  SHA256_Init(&context);
  SHA256_Update(&context, input.data(), input.length());
  unsigned char digest[SHA256_DIGEST_LENGTH];
  SHA256_Final(digest, &context);

  scoped_ptr_openssl_void<EVP_PKEY, EVP_PKEY_free> pkey(
      X509_get_pubkey(cert_.get()));
  if (!pkey.get()) {
    return false;
  }
  if (EVP_PKEY_type(pkey->type) != EVP_PKEY_RSA) {
    return false;
  }
  scoped_ptr_openssl_void<RSA, RSA_free> key(EVP_PKEY_get1_RSA(pkey.get()));
  return RSA_verify(NID_sha256, digest, SHA256_DIGEST_LENGTH,
                    StringToBytes(input), input.length(), key.get());
}

// *** CertificateSR ***

CertificateSR::CertificateSR() { request_.reset(X509_REQ_new()); }

bool CertificateSR::SetPublicKey(RSAKey* key) {
  scoped_ptr_openssl_void<EVP_PKEY, EVP_PKEY_free> pkey(EVP_PKEY_new());
  EVP_PKEY_set1_RSA(pkey.get(), key->get());
  return X509_REQ_set_pubkey(request_.get(), pkey.get());
}

bool CertificateSR::SetSubject(const std::string& subject) {
  scoped_ptr_openssl_void<X509_NAME, X509_NAME_free> name(X509_NAME_new());
  X509_NAME_add_entry_by_NID(
      name.get(), NID_commonName, MBSTRING_ASC,
      const_cast<unsigned char*>(StringToBytes(subject.data())),
      subject.length(), -1, 0);
  return X509_REQ_set_subject_name(request_.get(), name.get());
}

std::string CertificateSR::ToStringPEM() const {
  if (request_.get() == NULL) {
    return "";
  }
  scoped_ptr_openssl_int<BIO, BIO_free> bio(BIO_new(BIO_s_mem()));
  if (!PEM_write_bio_X509_REQ(bio.get(), request_.get())) {
    return "";
  }
  return BIOToString(bio.get());
}

bool CertificateSR::Sign(RSAKey* key) {
  scoped_ptr_openssl_void<EVP_PKEY, EVP_PKEY_free> pkey(EVP_PKEY_new());
  EVP_PKEY_set1_RSA(pkey.get(), key->get());
  return X509_REQ_sign(request_.get(), pkey.get(), EVP_sha1());
}

// *** AES128CBCCipher ***
std::string AES128CBCCipher::Encrypt(const std::string& key,
                                     const std::string& iv,
                                     const std::string& input) {
  const EVP_CIPHER* cipher = EVP_aes_128_cbc();
  if (input.empty() || key.size() != EVP_CIPHER_key_length(cipher) ||
      iv.size() != EVP_CIPHER_iv_length(cipher)) {
    return "";
  }
  EVP_CIPHER_CTX context;
  EVP_CIPHER_CTX_init(&context);
  EVP_EncryptInit_ex(&context, EVP_aes_128_cbc(), NULL, StringToBytes(key),
                     StringToBytes(iv));
  EVP_CIPHER_CTX_set_padding(&context, 1);
  const int max_output_size = input.length() + EVP_CIPHER_block_size(cipher);
  std::unique_ptr<unsigned char[]> output(new unsigned char[max_output_size]);
  int update_length;
  EVP_EncryptUpdate(&context, output.get(), &update_length,
                    StringToBytes(input), input.size());
  int final_length;
  EVP_EncryptFinal_ex(&context, output.get() + update_length, &final_length);
  EVP_CIPHER_CTX_cleanup(&context);
  return std::string(reinterpret_cast<const char*>(output.get()),
                     update_length + final_length);
}

std::string AES128CBCCipher::Decrypt(const std::string& key,
                                     const std::string& iv,
                                     const std::string& input) {
  const EVP_CIPHER* cipher = EVP_aes_128_cbc();
  if (input.empty() || key.size() != EVP_CIPHER_key_length(cipher) ||
      iv.size() != EVP_CIPHER_iv_length(cipher)) {
    return "";
  }
  EVP_CIPHER_CTX context;
  EVP_CIPHER_CTX_init(&context);
  EVP_DecryptInit_ex(&context, EVP_aes_128_cbc(), NULL, StringToBytes(key),
                     StringToBytes(iv));
  EVP_CIPHER_CTX_set_padding(&context, 1);
  const int max_output_size = input.length() + EVP_CIPHER_block_size(cipher);
  std::unique_ptr<unsigned char[]> output(new unsigned char[max_output_size]);
  int update_length;
  EVP_DecryptUpdate(&context, output.get(), &update_length,
                    StringToBytes(input), input.size());
  int final_length;
  EVP_DecryptFinal_ex(&context, output.get() + update_length, &final_length);
  EVP_CIPHER_CTX_cleanup(&context);
  return std::string(reinterpret_cast<const char*>(output.get()),
                     update_length + final_length);
}

//  *** CryptoRand ***
std::string CryptoRand::RandBytes(int num_bytes) {
  std::unique_ptr<unsigned char[]> output(new unsigned char[num_bytes]);
  if (!RAND_bytes(output.get(), num_bytes)) {
    return "";
  }
  return std::string(reinterpret_cast<const char*>(output.get()), num_bytes);
}

uint64 CryptoRand::RandInt64() {
  unsigned char output[8];
  if (!RAND_bytes(output, 8)) {
    return 0UL;
  }
  return *(reinterpret_cast<uint64*>(output));
}

}  // namespace grr
