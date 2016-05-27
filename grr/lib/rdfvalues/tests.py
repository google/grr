#!/usr/bin/env python
# Copyright 2012 Google Inc. All Rights Reserved.
"""GRR rdfvalue tests.

This module loads and registers all the tests for the RDFValue implementations.
"""



# These need to register plugins so, pylint: disable=unused-import
from grr.lib.rdfvalues import aff4_rdfvalues_test
from grr.lib.rdfvalues import basic_test
from grr.lib.rdfvalues import benchmark_test
from grr.lib.rdfvalues import client_test
from grr.lib.rdfvalues import crypto_test
from grr.lib.rdfvalues import data_store_test
from grr.lib.rdfvalues import filestore_test
from grr.lib.rdfvalues import flows_test
from grr.lib.rdfvalues import foreman_test
from grr.lib.rdfvalues import paths_test
from grr.lib.rdfvalues import protodict_test
from grr.lib.rdfvalues import standard_test
from grr.lib.rdfvalues import stats_test
from grr.lib.rdfvalues import structs_test
