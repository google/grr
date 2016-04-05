
#include "grr/client/minicomm/client.h"

int main(int argc, char* argv[]) {
  grr::Client::StaticInit();
  if (argc != 2) {
    GOOGLE_LOG(FATAL) << "Usage is: client <config>";
  }
  grr::Client client(argv[1]);
  client.Run();
  return 0;
}
