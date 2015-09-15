#include "grr/client/minicomm/http_connection.h"

#include <math.h>
#include <stddef.h>
#include <time.h>

#include <sstream>
#include <algorithm>
#include <chrono>
#include <ostream>
#include <ratio>
#include <string>
#include <thread>
#include <vector>

#include "curl/curl.h"

#include "grr/client/minicomm/comms_utils.h"
#include "grr/client/minicomm/crypto.h"
#include "grr/client/minicomm/resource_monitor.h"
#include "grr/client/minicomm/util.h"
#include "grr/proto/jobs.pb.h"

namespace grr {
namespace {
struct HttpResponse {
  long http_response_code;
  std::string headers;
  std::string body;
};

size_t write_ostringstream(char* ptr, size_t size, size_t nmemb,
                           void* userdata) {
  *reinterpret_cast<std::ostringstream*>(userdata)
      << std::string(ptr, size * nmemb);
  return size * nmemb;
}

// Make a request to url. If proxy is non-empty, use it as a proxy server.
// If post_data is non-empty, make a post request.
HttpResponse RequestURL(const std::string& url, const std::string& proxy,
                        const std::string& post_data) {
  std::ostringstream headers;
  std::ostringstream body;
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
  std::vector<std::string> control_urls(config_->ControlUrls());
  std::vector<std::string> proxy_servers(config_->ProxyServers());
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
      if (server_pem.find("BEGIN CERTIFICATE") == std::string::npos) {
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
      GOOGLE_LOG(INFO) << "Connection established to: " << url;
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
  std::vector<GrrMessage> to_send;

  NonceGenerator nonce_gen;
  NetworkResourceMonitor network;
  HardwareResourceMonitor hardware(outbox_);

  while (true) {
    // If the last try was a failure, wait 5 seconds before retrying. Otherwise
    // wait depending on how long it has been since there was some activity.
    if (failed) {
      std::this_thread::sleep_for(std::chrono::seconds(5));
    } else {
      const int delay_millis = std::min(
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

    if (network.WaitToSend(to_send) == false) {
      // In case too much outgoing bandwidth would be used, drop the packet.
      // TODO(user): Save network packet and send it later.
      to_send.clear();
      continue;
    }

    const uint64 nonce = nonce_gen.Generate();
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

    hardware.ClientEnrolled();  // Notify hardware resource monitor that the
                                // client has successfully enrolled.
    if (to_send.size()) {
      // We succeeded in sending to_send.
      GOOGLE_LOG(INFO) << "Sent " << to_send.size() << " messages.";
    }
    to_send.clear();

    ClientCommunication result;
    if (!result.ParseFromString(response.body)) {
      failed = true;
      continue;
    }
    std::vector<GrrMessage> messages;
    if (!current_connection_->secure_session().DecodeMessages(result, &messages,
                                                              nonce)) {
      GOOGLE_LOG(ERROR) << "Failed to decode response.";
      failed = true;
      continue;
    }
    if (messages.size()) {
      GOOGLE_LOG(INFO) << "Decoded response with " << messages.size()
                       << " messages.";
    }
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
