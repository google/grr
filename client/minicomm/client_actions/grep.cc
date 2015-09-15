#include "grr/client/minicomm/client_actions/grep.h"

#include <algorithm>

#include "grr/client/minicomm/file_contents.h"
#include "grr/client/minicomm/paths.h"
#include "boost/regex.hpp"

namespace grr {
namespace actions {
void Grep::ProcessRequest(ActionContext* context) {
  GrepSpec req;
  if (!context->PopulateArgs(&req)) {
    return;
  }

  std::string error;
  auto result = Paths::NormalizeAndOpen(req.mutable_target(), &error);
  if (result == nullptr) {
    context->SetError(error);
    return;
  }
  if (result->size() == 0) {
    return;
  }

  // Try to be careful to avoid overflows.
  const uint64 start_idx = std::min(req.start_offset(), result->size());
  const uint64 end_idx =
      start_idx + std::min(result->size() - start_idx, req.length());
  if (start_idx == end_idx) {
    context->SetError(
        "Attempt to grep empty interval. Start offset too large?");
    return;
  }

  FileContents contents(result.get());
  const FileContentsIterator start_pos(start_idx, &contents);
  const FileContentsIterator end_pos(end_idx, &contents);

  std::vector<Match> matches;
  if (req.has_literal()) {
    matches = SearchLiteral(req.literal(), start_pos, end_pos,
                            req.mode() == GrepSpec::ALL_HITS);
  } else {
    error = "";
    matches = SearchRegex(req.regex(), start_pos, end_pos,
                          req.mode() == GrepSpec::ALL_HITS, &error);
    if (!error.empty()) {
      context->SetError(error);
      return;
    }
  }
  for (Match m : matches) {
    BufferReference res;
    *res.mutable_pathspec() = req.target();

    // Start and end expanded to include any needed extra bytes.
    const auto expanded_match_start =
        m.match_start -
        std::min(static_cast<uint64>(m.match_start.FileOffset()),
                 static_cast<uint64>(req.bytes_before()));
    const auto expanded_match_end =
        m.match_end + std::min(static_cast<uint64>(req.bytes_after()),
                               static_cast<uint64>(result->size() -
                                                   m.match_end.FileOffset()));

    res.set_offset(expanded_match_start.FileOffset());
    res.set_length(expanded_match_end.FileOffset() -
                   expanded_match_start.FileOffset());
    res.set_data(std::string(expanded_match_start, expanded_match_end));

    context->SendResponse(res, GrrMessage::MESSAGE);
  }
}

std::vector<Grep::Match> Grep::SearchLiteral(const std::string& literal,
                                             FileContentsIterator start_pos,
                                             FileContentsIterator end_pos,
                                             bool all_hits) {
  std::vector<Match> res;
  while (end_pos != (start_pos = std::search(start_pos, end_pos,
                                             literal.begin(), literal.end()))) {
    res.emplace_back(Match{start_pos, start_pos + literal.size()});
    if (!all_hits) {
      return res;
    }
    start_pos += literal.size();
  }
  return res;
}

std::vector<Grep::Match> Grep::SearchRegex(const std::string& regex,
                                           FileContentsIterator start_pos,
                                           FileContentsIterator end_pos,
                                           bool all_hits, std::string* error) {
  std::vector<Match> res;
  boost::regex pattern(regex, (boost::regex_constants::ECMAScript |
                               boost::regex_constants::no_except));
  if (pattern.status()) {
    *error = "Unable to parse regex [" + regex + "]";
    return res;
  }
  typedef boost::regex_iterator<FileContentsIterator> re_iter;
  for (auto i = re_iter(start_pos, end_pos, pattern); i != re_iter(); ++i) {
    auto& m = *i;
    res.emplace_back(Match{m[0].first, m[0].second});
    if (!all_hits) {
      return res;
    }
  }
  return res;
}
}  // namespace actions
}  // namespace grr
