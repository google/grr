"""
Stubs of OSQuery client actions.

Similar pattern as server_stubs

@author: ashaman
"""
from grr.server.server_stubs import ClientActionStub
from grr.lib.rdfvalues import osquery as rdf_client_osquery

class ExecuteOSQuerySQL(ClientActionStub):
  """Run an OSQuery"""

  in_rdfvalue = rdf_client_osquery.OSQueryRunQueryArgs
  out_rdfvalues = [rdf_client_osquery.OSQueryRunQueryResult]