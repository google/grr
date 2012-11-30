#!/usr/bin/env python
# Copyright 2012 Google Inc.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


"""Module containing a set of reports for management of GRR."""

import csv
import datetime
import operator
import StringIO
import time

import logging

from grr.lib import aff4
from grr.lib import email_alerts
from grr.lib.aff4_objects import aff4_grr


class ClientReport(object):
  """The baseclass of all client reports."""

  EMAIL_TEMPLATE = """
  <html><body><h2>%(report_name)s</h2>
  %(report_text)s
  <br/>
  <p>Thanks,</p>
  <p>The GRR team.
  </body></html>"""
  EMAIL_FROM = "noreply"

  def __init__(self, token):
    self.token = token
    self.results = []
    self.broken_subjects = []  #  Database entries that are broken.
    self.fields = [f.name for f in self.REPORT_ATTRS]

  def AsDict(self):
    """Give the report as a list of dicts."""
    if not self.results:
      logging.warn("Run has not been called, no results.")
    else:
      return self.results

  def AsCsv(self):
    """Give the report in CSV format."""
    output = StringIO.StringIO()
    writer = csv.DictWriter(output, self.fields)
    if hasattr(writer, "writeheader"):
      writer.writeheader()  # requires 2.7
    for val in self.results:
      writer.writerow(val)
    output.seek(0)
    return output

  def SortResults(self, field):
    """Sort the result set."""
    logging.debug("Sorting %d results", len(self.results))
    self.results.sort(key=operator.itemgetter(field))

  def AsHtmlTable(self):
    """Return the results as an HTML table."""
    th = ["<th>%s</th>" % f for f in self.fields]
    headers = "<tr>%s</tr>" % "".join(th)
    rows = []
    for val in self.results:
      values = [val[k] for k in self.fields]
      row = ["<td>%s</td>" % f for f in values]
      rows.append("<tr>%s</tr>" % "".join(row))
    html_out = "<table>%s%s</table>" % (headers, "\n".join(rows))
    return html_out

  def AsText(self):
    """Give the report as formatted text."""
    output = StringIO.StringIO()
    fields = self.fields
    writer = csv.DictWriter(output, fields, dialect=csv.excel_tab)
    for val in self.results:
      writer.writerow(val)
    output.seek(0)
    return output

  def MailReport(self, recipient, subject=None):
    """Mail the HTML report to recipient."""
    if subject is None:
      subject = self.REPORT_NAME
    report_text = self.AsHtmlTable()
    email_alerts.SendEmail(recipient, self.EMAIL_FROM,
                           subject,
                           self.EMAIL_TEMPLATE % dict(
                               report_text=report_text,
                               report_name=self.REPORT_NAME),
                           is_html=True)
    logging.info("Report %s mailed to %s", self.REPORT_NAME, recipient)

  def Run(self, max_age=60*60*24*7):
    """Run the report.

    Args:
      max_age: Maximum age in seconds of the client to include in report.
    """
    pass

  def _QueryResults(self, max_age):
    """Query each record in the client database."""
    root = aff4.FACTORY.Open(aff4.ROOT_URN, token=self.token)
    for count, child in enumerate(root.OpenChildren(chunk_limit=1000000)):
      if count % 2000 == 0:
        logging.info("%s %d clients processed.", self.REPORT_NAME, count)

      if isinstance(child, aff4_grr.VFSGRRClient):
        # Skip if older than max_age
        oldest_time = (time.time() - max_age) * 1e6
        if child.Get(aff4.Attribute.GetAttributeByName("Clock")) < oldest_time:
          continue

        result = {}
        for attr in self.REPORT_ATTRS:
          # Do some special formatting for certain fields.
          if attr.name == "subject":
            result[attr.name] = child.Get(attr).Basename()
          elif attr.name == "GRR client":
            c_info = child.Get(attr)
            if not c_info:
              self.broken_subjects.append(child.client_id)
              result[attr.name] = None
              continue

            result[attr.name] = "%s %s" % (c_info.data.client_name,
                                           str(c_info.data.client_version))
          else:
            result[attr.name] = child.Get(attr)
        yield result


class ClientListReport(ClientReport):
  """Returns a list of clients with their version."""

  REPORT_ATTRS = [
      aff4.Attribute.GetAttributeByName("Clock"),
      aff4.Attribute.GetAttributeByName("subject"),
      aff4.Attribute.GetAttributeByName("Host"),
      aff4.Attribute.GetAttributeByName("System"),
      aff4.Attribute.GetAttributeByName("Architecture"),
      aff4.Attribute.GetAttributeByName("GRR client")
  ]

  REPORT_NAME = "GRR Client List Report"

  def Run(self, max_age=60*60*24*7):
    """Collect all the data for the report."""
    start_time = time.time()
    self.results = []
    self.broken_subjects = []
    for client in self._QueryResults(max_age):
      self.results.append(client)
    self.SortResults("GRR client")
    logging.info("%s took %s to complete", self.REPORT_NAME,
                 datetime.timedelta(seconds=time.time() - start_time))


class VersionBreakdownReport(ClientReport):
  """Returns a breakdown of versions."""

  REPORT_ATTRS = [
      aff4.Attribute.GetAttributeByName("GRR client")
  ]
  REPORT_NAME = "GRR Client Version Breakdown Report"

  def Run(self, max_age=60*60*24*7):
    """Run the report."""
    counts = {}
    self.fields.append("count")
    self.results = []
    self.broken_subjects = []
    for client in self._QueryResults(max_age):
      version = client.get("GRR client")
      try:
        counts[version] += 1
      except KeyError:
        counts[version] = 1
    for version, count in counts.iteritems():
      self.results.append({"GRR client": version, "count": count})
    self.SortResults("count")
