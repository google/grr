#include "grr/client/minicomm/client_actions/grep.h"

#include <algorithm>

#include "grr/client/minicomm/paths.h"
#include "boost/regex.hpp"

namespace grr {
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

  const char* const mmap_offset = result->MMap(&error);
  if (mmap_offset == nullptr) {
    context->SetError(error);
    return;
  }

  const char* start_pos =
      mmap_offset + std::min(req.start_offset(), result->size());
  const char* end_pos =
      mmap_offset + std::min(req.start_offset() + req.length(), result->size());
  if (start_pos == end_pos) {
    context->SetError(
        "Attempt to grep empty interval. Start offset too large?");
    return;
  }

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

    // Start and end of the match within the file.
    const size_t file_start = m.start - mmap_offset;
    const size_t file_end = file_start + m.len;

    // Start and end expanded to include any needed extra bytes.
    const size_t expanded_file_start = file_start -
        std::min(file_start, size_t(req.bytes_before()));
    const size_t expanded_file_end = file_end +
        std::min(size_t(req.bytes_after()),
                 size_t(result->size() - file_end));

    res.set_offset(expanded_file_start);
    res.set_length(expanded_file_end - expanded_file_start);
    res.set_data(std::string(m.start, m.len));

    context->SendResponse(res, GrrMessage::MESSAGE);
  }
}

std::vector<Grep::Match> Grep::SearchLiteral(const std::string& literal,
                                             const char* start_pos,
                                             const char* end_pos,
                                             bool all_hits) {
  std::vector<Match> res;
  while (end_pos != (start_pos = std::search(start_pos, end_pos,
                                             literal.begin(), literal.end()))) {
    res.emplace_back(Match{start_pos, literal.size()});
    if (!all_hits) {
      return res;
    }
    start_pos += literal.size();
  }
  return res;
}

std::vector<Grep::Match> Grep::SearchRegex(const std::string& regex,
                                           const char* start_pos,
                                           const char* end_pos, bool all_hits,
                                           std::string* error) {
  std::vector<Match> res;
  boost::regex pattern(regex, (boost::regex_constants::ECMAScript |
                               boost::regex_constants::no_except));
  if (pattern.status()) {
    *error = "Unable to parse regex [" + regex + "]";
    return res;
  }
  for (auto i = boost::cregex_iterator(start_pos, end_pos, pattern);
       i != boost::cregex_iterator(); ++i) {
    auto& m = *i;
    res.emplace_back(Match{m[0].first, size_t(m[0].second - m[0].first)});
    if (!all_hits) {
      return res;
    }
  }
  return res;
}
}  // namespace grr
