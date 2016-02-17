#!/usr/bin/env python
"""Load all rdfvalues in this directory to populate the registry.
"""
# These need to register plugins so, pylint: disable=unused-import
from grr.lib.rdfvalues import aff4_rdfvalues
from grr.lib.rdfvalues import anomaly
from grr.lib.rdfvalues import client
from grr.lib.rdfvalues import config_file
from grr.lib.rdfvalues import cronjobs
from grr.lib.rdfvalues import crypto
from grr.lib.rdfvalues import data_server
from grr.lib.rdfvalues import data_store
from grr.lib.rdfvalues import flows
from grr.lib.rdfvalues import grr_rdf
from grr.lib.rdfvalues import hunts
from grr.lib.rdfvalues import nsrl
from grr.lib.rdfvalues import paths
from grr.lib.rdfvalues import plist
from grr.lib.rdfvalues import protodict
from grr.lib.rdfvalues import stats
from grr.lib.rdfvalues import structs
from grr.lib.rdfvalues import webhistory
from grr.lib.rdfvalues import wmi
