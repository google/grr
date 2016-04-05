#ifndef GRR_CLIENT_MINICOMM_CLIENT_ACTIONS_GREP_H_
#define GRR_CLIENT_MINICOMM_CLIENT_ACTIONS_GREP_H_

#include <vector>

#include "grr/client/minicomm/client_action.h"
#include "grr/client/minicomm/file_contents.h"

namespace grr {
namespace actions {
class Grep : public ClientAction {
 public:
  Grep() {}

  void ProcessRequest(ActionContext* args) override;

 private:
  struct Match {
    FileContentsIterator match_start;
    FileContentsIterator match_end;
  };
  std::vector<Match> SearchLiteral(const std::string& literal,
                                   FileContentsIterator begin,
                                   FileContentsIterator end,
                                   bool all_hits);

  std::vector<Match> SearchRegex(const std::string& regex,
                                 FileContentsIterator begin,
                                 FileContentsIterator end,
                                 bool all_hits, std::string* error);
};
}  // namespace actions
}  // namespace grr

#endif  // GRR_CLIENT_MINICOMM_CLIENT_ACTIONS_GREP_H_
