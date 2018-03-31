#!/usr/bin/env python
"""Execute OSQuery SQL."""

import re
import logging
import subprocess
import json
from grr_response_client import actions
from grr.lib.rdfvalues import osquery as rdf_osquery


class ExecuteOSQuerySQL(actions.ActionPlugin):
  """Execute OSQuery SQL."""
  in_rdfvalue = rdf_osquery.OSQueryRunQueryArgs
  out_rdfvalues = [rdf_osquery.OSQueryRunQueryResult]

  def Run(self, args):
    data = subprocess.check_output("osqueryi --json '%s' 2>&1" % args.query, shell=True)
    logging.debug("JSON output for query %s:  %s" % (args.query, data))

    if("Error" in data):
      #Why doesn't error_msg show up in the UI???
      matches = re.findall(".*Error:(.+).*", data)
      result = rdf_osquery.OSQueryRunQueryResult()
      result.error_msg = matches[0]
      self.SendReply(result)
    else:
      row_data = json.loads(data)

      for row in row_data:
        result = rdf_osquery.OSQueryRunQueryResult()
        for key, value in row.items():
          resultult_field = getattr(result,key)
          resultult_field.append(value)

        self.SendReply(result)
