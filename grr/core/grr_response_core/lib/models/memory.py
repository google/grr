#!/usr/bin/env python
"""Proto functions used with Yara."""

from grr_response_proto import flows_pb2


def CreateYaraProcessScanRequest(
    include_errors_in_results: flows_pb2.YaraProcessScanRequest.ErrorPolicy = flows_pb2.YaraProcessScanRequest.ErrorPolicy.NO_ERRORS,
    include_misses_in_results: bool = False,
    ignore_grr_process: bool = True,
    chunk_size: int = 100 * 1024 * 1024,
    overlap_size: int = 10 * 1024 * 1024,
    skip_special_regions: bool = False,
    skip_mapped_files: bool = True,
    skip_shared_regions: bool = False,
    skip_executable_regions: bool = False,
    skip_readonly_regions: bool = False,
    dump_process_on_match: bool = False,
    process_dump_size_limit: int = 0,
    context_window: int = 50,
) -> flows_pb2.YaraProcessScanRequest:
  """Creates a YaraProcessScanRequest with default values."""

  return flows_pb2.YaraProcessScanRequest(
      include_errors_in_results=include_errors_in_results,
      include_misses_in_results=include_misses_in_results,
      ignore_grr_process=ignore_grr_process,
      chunk_size=chunk_size,
      overlap_size=overlap_size,
      skip_special_regions=skip_special_regions,
      skip_mapped_files=skip_mapped_files,
      skip_shared_regions=skip_shared_regions,
      skip_executable_regions=skip_executable_regions,
      skip_readonly_regions=skip_readonly_regions,
      dump_process_on_match=dump_process_on_match,
      process_dump_size_limit=process_dump_size_limit,
      context_window=context_window,
  )
