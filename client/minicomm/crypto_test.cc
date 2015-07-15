#include "grr/client/minicomm/crypto.h"

#include "gtest/gtest.h"

namespace grr {

TEST(CryptoTest, DigestSha256) {
  static const std::string plaintext(
      "Machines take me by surprise with great frequency");
  static const std::string hash(
      "\xd2\x54\x33\xd0\xd9\x80\xeb\x5d\xc4\x7e\xcd\x71\x74\xa0\x1c\xa4\x41\xad"
      "\xe6\x46\x08\x35\x07\x4a\x46\x7e\x77\xd9\x83\x43\xc9\x0b",
      256 / 8);
  static const std::string empty_hash(
      "\xe3\xb0\xc4\x42\x98\xfc\x1c\x14\x9a\xfb\xf4\xc8\x99\x6f\xb9\x24\x27\xae"
      "\x41\xe4\x64\x9b\x93\x4c\xa4\x95\x99\x1b\x78\x52\xb8\x55",
      256 / 8);
  EXPECT_EQ(Digest::Hash(Digest::Type::SHA256, plaintext), hash);
  EXPECT_EQ(Digest::Hash(Digest::Type::SHA256, ""), empty_hash);
}

TEST(CryptoText, HMAC) {
  static const std::string key("secret");
  static const std::string hash(
      "\x69\x4a\xbd\x10\x84\x2d\x16\x1d\xdb\xc5\x4d\xf8\xa0\xd5\x7c\xf6\x4d\x0d"
      "\xbc\xc9",
      160 / 8);
  Sha1HMAC hmac(key);
  hmac.Update("a");
  hmac.Update("b");
  hmac.Update("c");
  EXPECT_EQ(hmac.Final(), hash);

  static const std::string empty_hash(
      "\x25\xaf\x61\x74\xa0\xfc\xec\xc4\xd3\x46\x68\x0a\x72\xb7\xce\x64\x4b\x9a"
      "\x88\xe8",
      160 / 8);

  Sha1HMAC empty_hmac(key);
  EXPECT_EQ(empty_hmac.Final(), empty_hash);
}

TEST(CryptoTest, RSAKey) {
  RSAKey key;
  EXPECT_FALSE(key.FromPEM(""));
  EXPECT_FALSE(key.FromPEM("garbage in"));
  EXPECT_EQ(key.ToStringPEM(), "");

  key.Generate();
  std::string pem = key.ToStringPEM();
  GOOGLE_LOG(INFO) << pem;
  ASSERT_FALSE(pem.empty());

  RSAKey another_key;
  another_key.Generate();
  std::string another_pem = another_key.ToStringPEM();
  // Generate function must generate new keys every time.
  EXPECT_NE(pem, another_pem);

  RSAKey key2;
  ASSERT_TRUE(key2.FromPEM(pem));
  std::string pem2 = key2.ToStringPEM();
  EXPECT_EQ(pem2, pem);

  std::string signature =
      key.SignSha256("A message worthy of a John Handcock.");
  EXPECT_FALSE(signature.empty());

  RSAKey key3(key);
  std::string pem3(key3.ToStringPEM());
  EXPECT_EQ(pem3, pem);

  RSAKey key_copy;
  key_copy = key;
}

// TODO(user): Test verify
// TODO(user): Test RSAKey::Decrypt

const char kPEMString[] = R"(
-----BEGIN CERTIFICATE-----
MIIGSzCCBDOgAwIBAgIJANuxiXoZSEeoMA0GCSqGSIb3DQEBBQUAMFYxCzAJBgNV
BAYTAlVTMRQwEgYDVQQDEwtHUlIgVGVzdCBDQTExMC8GCSqGSIb3DQEJARYic2Vj
dXJpdHktaW5jaWRlbnRzLXRlYW1AZ29vZ2xlLmNvbTAeFw0xMTAyMTcxMDEyMTNa
Fw0yMTAyMTQxMDEyMTNaMFYxCzAJBgNVBAYTAlVTMRQwEgYDVQQDEwtHUlIgVGVz
dCBDQTExMC8GCSqGSIb3DQEJARYic2VjdXJpdHktaW5jaWRlbnRzLXRlYW1AZ29v
Z2xlLmNvbTCCAiIwDQYJKoZIhvcNAQEBBQADggIPADCCAgoCggIBAPFhTdYWwBp8
yU/+jn7ea6ZNPAJByiUxufBLKy8uKLB20VjMBdUmOp9Vo0MN4aoZSNvT1w5zNBmd
09OTG5+XX9FcxND18i5ZlT3ZaHqpUk3Yk7M5xPLQqG8ySwv0iq6j0hIqUe8P40u5
Jf7cLPK4x6bkuzAsHa1YHgCX30Vn/gVIqfn7b0JY0mObAe3OYVNlhwepFgD1LawP
3FdgXhSQDpBuXdE/A+pVwMN0BlGQF8aycWrNQzM0xCxQy2LP+gin6yJjNRYyBGNY
pNd6942/zaOH04L6M+10E7w/AsAxrT5nr+dIHZnL+I1odN/ZosesGhsqGaqsXVkl
pi5JIu+60Zf6aGXJX461rJloDQR1JGwFvVLGJjV4ug/TyQ3h5PIm3Ef4rZLIpu3s
0quwrIpKKxcH9INk2n3YP8GxV0+wyTTiU67mQarU31gKqEfgwCQTFvr8dZZoZbtC
AJTZOGvlpju4w5X0mGwlsL44XKfIpDkexSRZsj6dZuGyfxRpbn71+Ti9jC7KlZBM
wvX2Os3yVY/PLGz3VBPB45s2IrR3M33sB4DWtPrU/mWwVOpfX68hSae97qxqLPVN
UO6jCayTtitRPK5Wx55MM3xgqspVOmqfX7EwGO40QIPLbwk5XGezXcxdfjdsB4iC
YUYwy0Q1YmnnxT4LQIpyu8BpzS0WZIf9AgMBAAGjggEaMIIBFjAdBgNVHQ4EFgQU
NH/EbH8MewdxaZzmD8+SEDBxAhIwgYYGA1UdIwR/MH2AFDR/xGx/DHsHcWmc5g/P
khAwcQISoVqkWDBWMQswCQYDVQQGEwJVUzEUMBIGA1UEAxMLR1JSIFRlc3QgQ0Ex
MTAvBgkqhkiG9w0BCQEWInNlY3VyaXR5LWluY2lkZW50cy10ZWFtQGdvb2dsZS5j
b22CCQDbsYl6GUhHqDAPBgNVHRMBAf8EBTADAQH/MBEGCWCGSAGG+EIBAQQEAwIB
BjAJBgNVHRIEAjAAMC0GA1UdEQQmMCSBInNlY3VyaXR5LWluY2lkZW50cy10ZWFt
QGdvb2dsZS5jb20wDgYDVR0PAQH/BAQDAgEGMA0GCSqGSIb3DQEBBQUAA4ICAQBv
aC5mlaYxaYa0A/mfnWl2jiRw2oOAPmSTiOeaD+ifT130VO4Z41Td/nw3UHaxvvxy
g062EkVVpUNnbR3VdZKmeEcrL894vmWjDxSrX6a6ryxj/oio5JXetrGEz/073TOO
eNgsbFu14qg4BQ/w2POvtT8trYdLsKVcAXvyIqLkbi9E86TsMFaR1x5QtlTwQu6H
lSxVAXp+w9qmKC8mCt/075JB673YxWI0xvsltOmECCk24oWYWtuLNX++ky0MmIJe
z/NfrM3ilG8DlI+RlLBm4sQhNV4W7GptYUBq95RSf1WTCPLpIgNLjzGhNWZDhe56
XZqymiwNhJwBmHwZf9B5joigACOKgs3CkWpwu3S57mR9XEfDJynJi8kZEL1QgVU/
87irCllMm/g0DqygEe+4eGEUH6YRfz34ATL/grT+1iFCg2nVOQ7ougJf8ACB4T2O
/bXEzcPGCOTvAO5qM+vNzsvPTqgfpBZ8vYJVN0zfSyj79JlVcnswt4VRUu8m4FHi
nuxV6Jjx7uKOUpyyKJQn9qCtFSUGqs1nj8ZmcSHR1epKOqFYdNB2MFEkVnLhi7a5
rGpa2OCau5VObCfY25ldCr0lAa2HiJjbIjA1upxho6/TBtaV6E01ez9c5WI4uo+U
ZApQ9jiqXUt8XvHtAM1rWXECV6beFXpZbqKmbQ+yxg==
-----END CERTIFICATE-----)";

TEST(CryptoTest, CertificateFromPEM) {
  Certificate cert;
  ASSERT_TRUE(cert.FromPEM(kPEMString));
  EXPECT_FALSE(cert.Encrypt("A key.").empty());
  Certificate cert2(cert);
  EXPECT_FALSE(cert2.Encrypt("A key.").empty());
}

TEST(CryptoTest, CertificateFromRSA) {
  RSAKey rsa_key;
  rsa_key.Generate();

  Certificate cert(rsa_key);
  EXPECT_FALSE(cert.ToStringPEM().empty());

  static const std::string kSecret = "secret";
  // TODO(user): Refactor the code to make it clear from
  // its types whether an RSAKey contains a private key or not.
  // Add appropriate testcases making sure we don't expose private
  // keys in unexpected ways - here we need to make sure the cert
  // doesn't contain any private key info.
  EXPECT_EQ(rsa_key.Decrypt(cert.Encrypt(kSecret)), kSecret);
}

TEST(CryptoTest, AES128CBCCipher) {
  std::string key("abcdefghijklmnopqrst", 16);
  std::string iv("tsrqponmlkjihgfedcba", 16);
  const std::string test_string(
      "The quick brown fox jumped over the lazy dogs.");
  const std::string encrypted = AES128CBCCipher::Encrypt(key, iv, test_string);
  ASSERT_FALSE(encrypted.empty());
  const std::string decrypted = AES128CBCCipher::Decrypt(key, iv, encrypted);
  EXPECT_EQ(test_string, decrypted);
}

TEST(CryptoTest, CryptoRand) {
  std::string bytes = CryptoRand::RandBytes(32);
  EXPECT_EQ(bytes.length(), 32);
  const uint64 r = CryptoRand::RandInt64();
  EXPECT_NE(r, 0UL);
}

}  // namespace grr
