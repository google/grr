#!/usr/bin/env python
"""End to end tests rewrite using GRR API."""

from grr_response_test.end_to_end_tests.tests import administrative
from grr_response_test.end_to_end_tests.tests import artifacts
from grr_response_test.end_to_end_tests.tests import checks
from grr_response_test.end_to_end_tests.tests import discovery
from grr_response_test.end_to_end_tests.tests import file_finder
from grr_response_test.end_to_end_tests.tests import filesystem
from grr_response_test.end_to_end_tests.tests import fingerprint
from grr_response_test.end_to_end_tests.tests import limits
from grr_response_test.end_to_end_tests.tests import memory
from grr_response_test.end_to_end_tests.tests import network
from grr_response_test.end_to_end_tests.tests import osquery
from grr_response_test.end_to_end_tests.tests import processes
from grr_response_test.end_to_end_tests.tests import registry
from grr_response_test.end_to_end_tests.tests import timeline
from grr_response_test.end_to_end_tests.tests import transfer
