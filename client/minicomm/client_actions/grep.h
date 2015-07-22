#ifndef GRR_CLIENT_MINICOMM_CLIENT_ACTIONS_GREP_H_
#define GRR_CLIENT_MINICOMM_CLIENT_ACTIONS_GREP_H_

#include <vector>

#include "grr/client/minicomm/client_action.h"

namespace grr {
namespace actions {
class Grep : public ClientAction {
 public:
  Grep() {}

  void ProcessRequest(ActionContext* args) override;

 private:
  struct Match {
    const char* start;
    size_t len;
  };
  std::vector<Match> SearchLiteral(const std::string& literal,
                                   const char* start_pos, const char* end_pos,
                                   bool all_hits);

  std::vector<Match> SearchRegex(const std::string& regex,
                                 const char* start_pos, const char* end_pos,
                                 bool all_hits, std::string* error);
};
}  // namespace actions
}  // namespace grr

#endif  // GRR_CLIENT_MINICOMM_CLIENT_ACTIONS_GREP_H_
