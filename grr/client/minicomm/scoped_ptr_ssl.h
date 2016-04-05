#ifndef GRR_CLIENT_MINICOMM_SCOPED_PTR_SSL_H_
#define GRR_CLIENT_MINICOMM_SCOPED_PTR_SSL_H_

// This file defines scoped pointer templates that are used to wrap OpenSSL
// pointer types that have OpenSSL-specific deallocation functions.  The object
// are created (or reference obtained if the object is reference counted by
// OpenSSL internally) by some OpenSSL function, but must be deallocated using a
// type-specific free function.  These scoped pointers makes it easier to use
// these OpenSSL objects without worrying about leaking memory/references.  The
// primary user is sign.cc and cert.cc, which insulates the user from having to
// deal with the lower-level OpenSSL types.

// The OpenSSL types use the naming convention of BIO *, BIO_free; EVP_PKEY *,
// EVP_PKEY_free; etc.

// Since the return type is not part of the type signature, we have to encode in
// the return type of the deallocation function in the templated class name.

// Supports move, but not copy, as copies require specific knowledge about the
// openssl type.

#include "grr/client/minicomm/base.h"  // GOOGLE_CHECK

template <typename OpenSSLType, void (*deallocator)(OpenSSLType *)>
class scoped_ptr_openssl_void {
 public:
  scoped_ptr_openssl_void() : ptr_(NULL) {}
  explicit scoped_ptr_openssl_void(OpenSSLType *p) : ptr_(p) {
    // we do not do
    //
    //  GOOGLE_CHECK(NULL != p) << ": scoped_ptr_openssl_int"
    //                   << " constructed with NULL pointer";
    //
    // here, since OpenSSL constructor-like allocators/transformers returns a
    // NULL on various error conditions that should not necessarily trigger an
    // abort.  For example, if we try to load an invalid cert,
    // PEM_read_bio_X509_AUX which transforms a string representation of an X509
    // cert to an X509 object will return a NULL; in such a case a server
    // application program would want to check this->get() and handle the error
    // (e.g., by rejecting the client) rather than aborting in a GOOGLE_CHECK.
  }
  ~scoped_ptr_openssl_void() {
    if (NULL != ptr_) {
      (*deallocator)(ptr_);
    }
  }
  OpenSSLType *operator->() const { return ptr_; }
  OpenSSLType *get() const { return ptr_; }
  OpenSSLType *release() {
    OpenSSLType *ret = ptr_;
    ptr_ = NULL;
    return ret;
  }
  void reset(OpenSSLType *p) {
    if (NULL != ptr_) {
      (*deallocator)(ptr_);
    }
    ptr_ = p;
  }
  scoped_ptr_openssl_void(scoped_ptr_openssl_void &&other) {
    ptr_ = other.release();
  }
  scoped_ptr_openssl_void(const scoped_ptr_openssl_void &other) = delete;
  void operator=(const scoped_ptr_openssl_void &other) = delete;

 private:
  OpenSSLType *ptr_;
};

template <typename OpenSSLType, int (*deallocator)(OpenSSLType *)>
class scoped_ptr_openssl_int {
 public:
  explicit scoped_ptr_openssl_int(OpenSSLType *p) : ptr_(p) { ; }
  ~scoped_ptr_openssl_int() { DeleteInternal(); }
  OpenSSLType *get() const { return ptr_; }
  OpenSSLType *release() {
    OpenSSLType *ret = ptr_;
    ptr_ = NULL;
    return ret;
  }
  void reset(OpenSSLType *p) {
    DeleteInternal();
    ptr_ = p;
  }
  scoped_ptr_openssl_int(scoped_ptr_openssl_int &&other) {
    ptr_ = other.release();
  }
  scoped_ptr_openssl_int(const scoped_ptr_openssl_int &other) = delete;
  void operator=(const scoped_ptr_openssl_int &other) = delete;

 private:
  void DeleteInternal() {
    if (NULL != ptr_) {
      // OpenSSL's deallocator for BIO can simply decrement reference
      // counts and return, or trigger callbacks which can return
      // errors.  The convention is that a 0 is returned if
      // NULL==ptr_, 1 is returned if a successful deref/deallocation
      // occurred, and negative if a callback returned an error.
      //
      // DSO_free and ENGINE_free are the other two such, and there a
      // zero is an error caused by NULL pointers or finish function
      // failures.

      int deallocation_status = (*deallocator)(ptr_);
      // Fail fast on any error.
      GOOGLE_CHECK(deallocation_status == 1)
          << ": OpenSSL object deallocator returned " << deallocation_status
          << ", expected 1.";
    }
  }

  OpenSSLType *ptr_;
};

extern "C" {
extern void ERR_clear_error();  // to avoid pulling in extra, messy OpenSSL
                                // headers.
}

class ScopedOpenSSLErrorStackClearer {
 public:
  ~ScopedOpenSSLErrorStackClearer() { ERR_clear_error(); }
};

#endif  // GRR_CLIENT_MINICOMM_SCOPED_PTR_SSL_H_
