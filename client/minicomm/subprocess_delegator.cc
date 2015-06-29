#include "grr/client/minicomm/subprocess_delegator.h"

#include <signal.h>
#include <stddef.h>
#include <sys/wait.h>
#include <unistd.h>
#include <algorithm>
#include <chrono>
#include <ratio>
#include <string>
#include <vector>

#include "grr/client/minicomm/base.h"
#include "grr/client/minicomm/config.pb.h"
#include "grr/proto/jobs.pb.h"

namespace grr {
SubprocessDelegator::SubprocessDelegator(ClientConfig* config,
                                         MessageQueue* inbox,
                                         MessageQueue* outbox)
    : config_(config),
      inbox_(inbox),
      outbox_(outbox),
      child_pid_(0),
      writer_thread_([this]() { this->WriteLoop(); }),
      reader_thread_([this]() { this->ReadLoop(); }),
      error_thread_([this]() { this->ErrorLoop(); }) {}

SubprocessDelegator::~SubprocessDelegator() {
  std::unique_lock<std::mutex> pid_lock(child_pid_mutex_);
  while (child_pid_ > 0) {
    pid_lock.unlock();
    KillChildProcess();
    pid_lock.lock();
  }
  child_pid_ = -1;
  pid_lock.unlock();
  child_spawned_.notify_all();
  // Writer thread might now be waiting to read from the inbox. Add an empty
  // message to unstick it.
  inbox_->AddMessage(GrrMessage());
  writer_thread_.join();
  reader_thread_.join();
  error_thread_.join();
}

void SubprocessDelegator::StartChildProcess() {
  const ClientConfiguration::SubprocessConfig config_proto =
      config_->SubprocessConfig();
  if (config_proto.filename().empty()) {
    GOOGLE_LOG(ERROR) << "Subprocess not configured.";
    return;
  }
  std::unique_lock<std::mutex> pid_lock(child_pid_mutex_);
  // If there is already child, or we are shutting down, we do nothing.
  if (child_pid_ != 0) {
    return;
  }
  int stdin_fd[2];
  int stdout_fd[2];
  int stderr_fd[2];
  pipe(stdin_fd);
  pipe(stdout_fd);
  pipe(stderr_fd);
  child_pid_ = fork();
  if (child_pid_ == 0) {
    close(stdin_fd[1]);
    close(stdout_fd[0]);
    close(stderr_fd[0]);

    std::vector<const char*> newargv;
    newargv.reserve(config_proto.argv_size() + 2);
    newargv.push_back(config_proto.filename().c_str());
    for (const std::string& arg : config_proto.argv()) {
      newargv.push_back(arg.c_str());
    }
    newargv.push_back(NULL);

    std::vector<const char*> newenv;
    newenv.reserve(config_proto.env_size() + 1);
    for (const std::string& v : config_proto.env()) {
      newenv.push_back(v.c_str());
    }
    newenv.push_back(NULL);

    dup2(stdin_fd[0], STDIN_FILENO);
    if (stdin_fd[0] != STDIN_FILENO) {
      close(stdin_fd[0]);
    }
    dup2(stdout_fd[1], STDOUT_FILENO);
    if (stdout_fd[1] != STDOUT_FILENO) {
      close(stdout_fd[1]);
    }
    dup2(stderr_fd[1], STDERR_FILENO);
    if (stderr_fd[1] != STDERR_FILENO) {
      close(stderr_fd[1]);
    }

    if (execve(config_proto.filename().c_str(),
               const_cast<char* const*>(&newargv[0]),
               const_cast<char* const*>(&newenv[0]))) {
      // Failed to Exec. Report through stderr, then die quickly and without
      // side effects.
      static const char kExecveMessage[] = "Child Unable to execve!\n";
      write(STDERR_FILENO, kExecveMessage, sizeof(kExecveMessage) - 1);
      while (1) {
        _exit(1);
      }
    }
  }
  close(stdin_fd[0]);
  close(stdout_fd[1]);
  close(stderr_fd[1]);
  {
    std::unique_lock<std::mutex> write_lock(write_mutex_);
    write_stream_.reset(
        new google::protobuf::io::FileOutputStream(stdin_fd[1]));
  }
  {
    std::unique_lock<std::mutex> read_lock(read_mutex_);
    read_stream_.reset(new google::protobuf::io::FileInputStream(stdout_fd[0]));
  }
  {
    std::unique_lock<std::mutex> error_lock(error_mutex_);
    error_stream_.reset(
        new google::protobuf::io::FileInputStream(stderr_fd[0]));
  }
  pid_lock.unlock();
  child_spawned_.notify_all();
}

namespace {
bool TryWaitPID(pid_t pid) {
  const int result = waitpid(pid, nullptr, WNOHANG);
  if (result == pid) {
    return true;
  }
  if (result == 0) {
    return false;
  }
  GOOGLE_LOG(ERROR) << "Returned [" << result << "] waiting for pid [" << pid
                    << "]";
  return false;
}
}  // namespace

void SubprocessDelegator::KillChildProcess() {
  std::unique_lock<std::mutex> pid_lock(child_pid_mutex_);
  undead_children_.erase(std::remove_if(undead_children_.begin(),
                                        undead_children_.end(), &TryWaitPID),
                         undead_children_.end());

  // If there is no child, or if we are in the process of shutting down, do
  // nothing.
  if (child_pid_ <= 0) {
    return;
  }

  kill(child_pid_, SIGTERM);
  // Give it time to end gracefully, then be more definitive.
  std::this_thread::sleep_for(std::chrono::seconds(4));
  kill(child_pid_, SIGKILL);
  std::this_thread::sleep_for(std::chrono::seconds(1));

  if (!TryWaitPID(child_pid_)) {
    GOOGLE_LOG(WARNING) << "Unable to fully kill subprocess:" << child_pid_;

    // Refuse to raise too many zombies. Returning here means we failed and will
    // start over the next time a problem with the child process is noted.
    if (undead_children_.size() > 5) {
      GOOGLE_LOG(ERROR) << "Too many undead children.";
      return;
    }
    undead_children_.push_back(child_pid_);
  }
  child_pid_ = 0;

  // With a dead child, all the threads should get a broken pipe error, and
  // start waiting to check child_pid_. So we can take their locks and close
  // everything.
  {
    std::unique_lock<std::mutex> write_lock(write_mutex_);
    if (write_stream_ != nullptr) {
      write_stream_->Close();
      write_stream_.reset(nullptr);
    }
  }
  {
    std::unique_lock<std::mutex> read_lock(read_mutex_);
    if (read_stream_ != nullptr) {
      read_stream_->Close();
      read_stream_.reset(nullptr);
    }
  }
  {
    std::unique_lock<std::mutex> error_lock(error_mutex_);
    if (error_stream_ != nullptr) {
      error_stream_->Close();
      error_stream_.reset(nullptr);
    }
  }
}

void SubprocessDelegator::WriteLoop() {
  while (true) {
    std::vector<GrrMessage> messages = inbox_->GetMessages(100, 100000, true);
    GOOGLE_DCHECK_GT(messages.size(), 0);
    std::unique_lock<std::mutex> pid_lock(child_pid_mutex_);
    // If there isn't a working child process, try to make one, repeatedly if
    // necessary, but don't spin too hard in case we have a config error or
    // other persistent failure.
    while (child_pid_ == 0) {
      pid_lock.unlock();
      StartChildProcess();
      pid_lock.lock();
      if (child_pid_ == 0) {
        pid_lock.unlock();
        std::this_thread::sleep_for(std::chrono::seconds(30));
        pid_lock.lock();
      }
    }
    if (child_pid_ == -1) {
      return;
    }
    GOOGLE_DCHECK(write_stream_ != nullptr);
    std::unique_lock<std::mutex> write_lock(write_mutex_);
    pid_lock.unlock();
    {
      google::protobuf::io::CodedOutputStream coded_stream(write_stream_.get());
      for (const auto& message : messages) {
        const int size = message.ByteSize();
        coded_stream.WriteLittleEndian32(size);
        message.SerializeWithCachedSizes(&coded_stream);
      }
    }
    write_stream_->Flush();
  }
}

void SubprocessDelegator::ReadLoop() {
  bool read_failed = false;
  while (true) {
    if (read_failed) {
      KillChildProcess();
      read_failed = false;
    }
    std::unique_lock<std::mutex> pid_lock(child_pid_mutex_);
    if (child_pid_ == 0) {
      child_spawned_.wait(pid_lock, [this] { return this->child_pid_ != 0; });
    }
    if (child_pid_ == -1) {
      return;
    }
    // read_stream should be non-null while pid > 0, and will stay non-null
    // while we hold read_mutex_. It is important to release the pid lock so
    // that KillChildProcess can start (and signal) while we are blocked
    // reading.
    GOOGLE_DCHECK(read_stream_ != nullptr);
    std::unique_lock<std::mutex> read_lock(read_mutex_);
    pid_lock.unlock();

    google::protobuf::uint32 message_size;
    google::protobuf::io::CodedInputStream coded_stream(read_stream_.get());
    if (!coded_stream.ReadLittleEndian32(&message_size)) {
      GOOGLE_LOG(ERROR) << "Unable to read size, resetting the subprocess.";
      read_failed = true;
      continue;
    }
    // Assume messages are less that 2MB.
    if (message_size > 2 * 1024 * 1024) {
      GOOGLE_LOG(ERROR) << "Read bad size, resetting the subprocess.";
      read_failed = true;
      continue;
    }
    if (message_size == 0) {
      continue;
    }
    GrrMessage message;
    coded_stream.PushLimit(message_size);
    if (!message.ParseFromCodedStream(&coded_stream)) {
      GOOGLE_LOG(ERROR) << "Unable to read message, resetting the subprocess.";
      read_failed = true;
      continue;
    }
    read_lock.unlock();
    outbox_->AddMessage(message);
  }
}

void SubprocessDelegator::ErrorLoop() {
  while (true) {
    std::unique_lock<std::mutex> pid_lock(child_pid_mutex_);
    if (child_pid_ == 0) {
      child_spawned_.wait(pid_lock, [this] { return this->child_pid_ != 0; });
    }
    if (child_pid_ == -1) {
      return;
    }
    GOOGLE_DCHECK(error_stream_ != nullptr);
    std::unique_lock<std::mutex> error_lock(error_mutex_);
    pid_lock.unlock();

    std::string line;

    int read_size = 0;
    const char* buffer = nullptr;
    while (error_stream_->Next(reinterpret_cast<const void**>(&buffer),
                               &read_size)) {
      const char* start_pos = buffer;
      const char* eol_pos = std::find(start_pos, buffer + read_size, '\n');
      while (eol_pos != buffer + read_size) {
        line += std::string(start_pos, eol_pos - start_pos);
        if (!line.empty()) {
          GOOGLE_LOG(ERROR) << "From subprocess: " << line;
        }
        line.clear();
        start_pos = eol_pos + 1;
        eol_pos = std::find(start_pos, buffer + read_size, '\n');
      }
      line += std::string(start_pos, eol_pos - start_pos);
    }
    if (!line.empty()) {
      GOOGLE_LOG(ERROR) << "From subprocess: " << line;
    }
  }
}
}  // namespace grr
