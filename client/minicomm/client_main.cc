
#include "client.h"

DEFINE_string(config_filename, "", "Where to find the config file.");

int main(int argc, char* argv[]) {
  InitGoogle(argv[0], &argc, &argv, true);
  grr::Client::StaticInit();
  grr::Client client(FLAGS_config_filename);
  client.Run();
  return 0;
}
