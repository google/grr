#!/usr/bin/env python
"""Stubs for client actions of the Rekall component."""

from grr.client.components.rekall_support import rekall_types
from grr.lib import server_stubs
from grr.lib.rdfvalues import paths as rdf_paths


class WriteRekallProfile(server_stubs.ClientActionStub):
  """A client action to write a Rekall profile to the local cache."""

  in_rdfvalue = rekall_types.RekallProfile


class RekallAction(server_stubs.ClientActionStub):
  """Runs a Rekall command on live memory."""
  in_rdfvalue = rekall_types.RekallRequest
  out_rdfvalues = [rekall_types.RekallResponse]


class GetMemoryInformation(server_stubs.ClientActionStub):
  """Loads the driver for memory access and returns a Stat for the device."""

  in_rdfvalue = rdf_paths.PathSpec
  out_rdfvalues = [rekall_types.MemoryInformation]
