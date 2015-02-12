#include "http_connection.h"

#include <math.h>
#include <stddef.h>
#include <time.h>
#include <algorithm>
#include <chrono>
#include <ostream>
#include <ratio>
#include <string>
#include <thread>
#include <vector>

#include "curl/curl.h"

#include "../../proto/jobs.pb.h"
#include "comms_utils.h"
#include "crypto.h"
#include "util.h"

typedef google3::ops::security::grr::GrrMessage Message;

namespace grr {
namespace {
struct HttpResponse {
  long http_response_code;
  std::string headers;
  std::string body;
};

size_t write_ostringstream(char* ptr, size_t size, size_t nmemb,
                           void* userdata) {
  *reinterpret_cast<ostringstream*>(userdata) << std::string(ptr, size * nmemb);
  return size * nmemb;
}

// Make a request to url. If proxy is non-empty, use it as a proxy server.
// If post_data is non-empty, make a post request.
HttpResponse RequestURL(const std::string& url, const std::string& proxy,
                        const std::string& post_data) {
  ostringstream headers;
  ostringstream body;
  struct curl_slist* added_headers = NULL;
  added_headers = curl_slist_append(added_headers, "Cache-Control: no-cache");

  CURL* curl_handle = curl_easy_init();
  curl_easy_setopt(curl_handle, CURLOPT_URL, url.c_str());
  if (!proxy.empty()) {
    curl_easy_setopt(curl_handle, CURLOPT_PROXY, proxy.c_str());
  }
  if (!post_data.empty()) {
    curl_easy_setopt(curl_handle, CURLOPT_POSTFIELDSIZE, post_data.length());
    curl_easy_setopt(curl_handle, CURLOPT_POSTFIELDS, post_data.data());
    added_headers =
        curl_slist_append(added_headers, "Content-Type: binary/octet-stream");
  }

  curl_easy_setopt(curl_handle, CURLOPT_WRITEFUNCTION, write_ostringstream);
  curl_easy_setopt(curl_handle, CURLOPT_HEADERDATA, &headers);
  curl_easy_setopt(curl_handle, CURLOPT_WRITEDATA, &body);

  curl_easy_setopt(curl_handle, CURLOPT_NOPROGRESS, 1L);
  curl_easy_setopt(curl_handle, CURLOPT_HTTPHEADER, added_headers);
  curl_easy_perform(curl_handle);

  HttpResponse response;
  curl_easy_getinfo(curl_handle, CURLINFO_RESPONSE_CODE,
                    &response.http_response_code);
  response.headers = headers.str();
  response.body = body.str();

  curl_easy_cleanup(curl_handle);
  curl_slist_free_all(added_headers);
  return response;
}

}  // namespace

void HttpConnectionManager::StaticInit() {
  curl_global_init(CURL_GLOBAL_DEFAULT);
}

HttpConnectionManager::HttpConnectionManager(ClientConfig* config,
                                             MessageQueue* inbox,
                                             MessageQueue* outbox)
    : last_enrollment_(std::chrono::system_clock::now() - std::chrono::hours()),
      config_(config),
      inbox_(inbox),
      outbox_(outbox) {}

HttpConnectionManager::~HttpConnectionManager() {}

class HttpConnectionManager::Connection {
 public:
  Connection(const std::string& client_id, RSAKey our_key,
             std::unique_ptr<Certificate> target_cert_, const std::string& url,
             const std::string& proxy)
      : our_key_(our_key),
        secure_session_(client_id, &our_key_, std::move(target_cert_)),
        url_(url),
        proxy_(proxy) {}

  SecureSession& secure_session() { return secure_session_; }
  const std::string& url() { return url_; }
  const std::string& proxy() { return proxy_; }

 private:
  RSAKey our_key_;
  SecureSession secure_session_;
  const std::string url_;
  const std::string proxy_;
};

HttpConnectionManager::Connection*
HttpConnectionManager::TryEstablishConnection() {
  GOOGLE_LOG(INFO) << "Trying to make a connection.";
  vector<std::string> control_urls(config_->ControlUrls());
  vector<std::string> proxy_servers(config_->ProxyServers());
  // Also try direct connection.
  proxy_servers.push_back("");
  for (const std::string& url : control_urls) {
    for (const std::string& proxy : proxy_servers) {
      const HttpResponse r =
          RequestURL(UrlDirname(url) + "/server.pem", proxy, "");
      if (r.http_response_code != 200L) {
        return nullptr;
      }
      const std::string& server_pem = r.body;
      if (server_pem.find("BEGIN CERTIFICATE") == string::npos) {
        return nullptr;
      }
      std::unique_ptr<Certificate> cert(new Certificate());
      if (!cert->FromPEM(server_pem)) {
        return nullptr;
      }
      if (!config_->ca_cert().Verify(*cert.get())) {
        return nullptr;
      }
      RSAKey my_key(config_->key());
      return new Connection(config_->ClientId(), config_->key(),
                            std::move(cert), url, proxy);
    }
  }
  return nullptr;
}

void HttpConnectionManager::Run() {
  bool failed = false;
  int no_activity_count = 0;

  // Messages that we've removed from the queue, but haven't yet managed to send
  // to the server.
  vector<Message> to_send;

  GOOGLE_LOG(INFO) << "Entering cm loop.";
  while (true) {
    // If the last try was a failure, wait 5 seconds before retrying. Otherwise
    // wait depending on how long it has been since there was some activity.
    if (failed) {
      std::this_thread::sleep_for(std::chrono::seconds(5));
    } else {
      const int delay_millis = min(
          600000, static_cast<int>(1000 * 0.2 * pow(1.05, no_activity_count)));
      std::this_thread::sleep_for(std::chrono::milliseconds(delay_millis));
    }

    // Loop until we manage to create a connection.
    while (current_connection_.get() == nullptr) {
      current_connection_.reset(TryEstablishConnection());
      std::this_thread::sleep_for(std::chrono::seconds(1));
    }
    failed = false;
    // If we already have some messages to send, just send them.
    if (to_send.empty()) {
      to_send = outbox_->GetMessages(1000, 1000000, false);
    }
    const int timestamp = time(NULL);

    // Insted of trying to get a portable sub-second clock, we just add random
    // values to the standard second level clock.
    const uint64 rnd = CryptoRand::RandInt64();
    if (rnd == 0UL) {
      failed = true;
      continue;
    }
    // 2^20-1 = 1048575
    const uint64 nonce =
        timestamp * 1000000UL + (rnd & 0b1111111111111111111UL);
    HttpResponse response = RequestURL(current_connection_->url() + "?api=3",
                                       current_connection_->proxy(),
                                       current_connection_->secure_session()
                                           .EncodeMessages(to_send, nonce)
                                           .SerializeAsString());
    if (response.http_response_code == 406) {
      if ((std::chrono::system_clock::now() - last_enrollment_) >
          10 * std::chrono::minutes()) {
        GOOGLE_LOG(INFO) << "Initiating enrollment!";
        MessageBuilder::InitiateEnrollment(config_, outbox_);
        last_enrollment_ = std::chrono::system_clock::now();
      }
      failed = true;
      continue;
    }
    if (response.http_response_code != 200) {
      failed = true;
      continue;
    }
    // We succeeded in sending to_send.
    to_send.clear();

    SecureSession::ClientCommunication result;
    if (!result.ParseFromString(response.body)) {
      failed = true;
      continue;
    }
    vector<Message> messages;
    if (!current_connection_->secure_session().DecodeMessages(result, &messages,
                                                              nonce)) {
      GOOGLE_LOG(ERROR) << "Failed to decode response.";
      failed = true;
      continue;
    }
    GOOGLE_LOG(INFO) << "Decoded response with " << messages.size() << " messages.";
    if (messages.size() == 0 && to_send.size() == 0) {
      no_activity_count += 1;
    } else {
      no_activity_count = 0;
    }
    for (const auto& m : messages) {
      inbox_->AddMessage(m);
    }
  }
}

}  // namespace grr
