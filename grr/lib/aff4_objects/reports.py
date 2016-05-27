#!/usr/bin/env python
"""Module containing a set of reports for management of GRR."""

import csv
import datetime
import StringIO
import time

import logging

from grr.lib import config_lib
from grr.lib import email_alerts
from grr.lib import export_utils
from grr.lib import rdfvalue
from grr.lib import registry
from grr.lib.aff4_objects import aff4_grr
from grr.lib.aff4_objects import network


class Report(object):
  """The baseclass for all reports."""

  # Register a metaclass registry to track all reports.
  __metaclass__ = registry.MetaclassRegistry


class ClientReport(Report):
  """The baseclass of all client reports."""

  EMAIL_TEMPLATE = """
  <html><body><h2>%(report_name)s</h2>
  %(report_text)s
  <br/>
  <p>Thanks,</p>
  <p>%(signature)s</p>
  </body></html>"""
  EMAIL_FROM = "noreply"

  # List of attributes to add to the report from the / path in the client.
  REPORT_ATTRS = []
  # List of tuples of (path, attribute) to add to the report.
  EXTENDED_REPORT_ATTRS = []

  __abstract = True  # pylint: disable=g-bad-name

  def __init__(self, token=None, thread_num=20):
    self.token = token
    self.results = []
    self.fields = [f.name for f in self.REPORT_ATTRS]
    self.fields += [f[1].name for f in self.EXTENDED_REPORT_ATTRS]
    self.thread_num = thread_num
    self.broken_clients = []  # Clients that are broken or fail to run.

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
    self.results.sort(key=lambda x: str(x.get(field, "")))

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
    dt = rdfvalue.RDFDatetime().Now().Format("%Y-%m-%dT%H-%MZ")
    subject = subject or "%s - %s" % (self.REPORT_NAME, dt)
    csv_data = self.AsCsv()
    filename = "%s-%s.csv" % (self.REPORT_NAME, dt)
    email_alerts.EMAIL_ALERTER.SendEmail(
        recipient,
        self.EMAIL_FROM,
        subject,
        "Please find the CSV report file attached",
        attachments={filename: csv_data.getvalue()},
        is_html=False)
    logging.info("Report %s mailed to %s", self.REPORT_NAME, recipient)

  def MailHTMLReport(self, recipient, subject=None):
    """Mail the HTML report to recipient."""
    dt = rdfvalue.RDFDatetime().Now().Format("%Y-%m-%dT%H-%MZ")
    subject = subject or "%s - %s" % (self.REPORT_NAME, dt)
    report_text = self.AsHtmlTable()

    email_alerts.EMAIL_ALERTER.SendEmail(
        recipient,
        self.EMAIL_FROM,
        subject,
        self.EMAIL_TEMPLATE %
        dict(report_text=report_text,
             report_name=self.REPORT_NAME,
             signature=config_lib.CONFIG["Email.signature"]),
        is_html=True)
    logging.info("Report %s mailed to %s", self.REPORT_NAME, recipient)

  def Run(self, max_age=60 * 60 * 24 * 7):
    """Run the report.

    Args:
      max_age: Maximum age in seconds of the client to include in report.
    """
    pass

  def _QueryResults(self, max_age):
    """Query each record in the client database."""
    report_iter = ClientReportIterator(
        max_age=max_age,
        token=self.token,
        report_attrs=self.REPORT_ATTRS,
        extended_report_attrs=self.EXTENDED_REPORT_ATTRS)
    self.broken_clients = report_iter.broken_subjects
    return report_iter.Run()


class ClientListReport(ClientReport):
  """Returns a list of clients with their version."""

  REPORT_ATTRS = [
      aff4_grr.VFSGRRClient.SchemaCls.GetAttribute("LastCheckin"),
      aff4_grr.VFSGRRClient.SchemaCls.GetAttribute("subject"),
      aff4_grr.VFSGRRClient.SchemaCls.GetAttribute("Host"),
      aff4_grr.VFSGRRClient.SchemaCls.GetAttribute("System"),
      aff4_grr.VFSGRRClient.SchemaCls.GetAttribute("Architecture"),
      aff4_grr.VFSGRRClient.SchemaCls.GetAttribute("Uname"),
      aff4_grr.VFSGRRClient.SchemaCls.GetAttribute("GRR client"),
  ]

  EXTENDED_REPORT_ATTRS = [
      ("network", network.Network.SchemaCls.GetAttribute("Interfaces"))
  ]

  REPORT_NAME = "GRR Client List Report"

  def Run(self, max_age=60 * 60 * 24 * 7):
    """Collect all the data for the report."""
    start_time = time.time()
    self.results = []
    self.broken_subjects = []
    for client in self._QueryResults(max_age):
      self.results.append(client)
    self.SortResults("GRR client")
    logging.info("%s took %s to complete",
                 self.REPORT_NAME,
                 datetime.timedelta(seconds=time.time() - start_time))


class VersionBreakdownReport(ClientReport):
  """Returns a breakdown of versions."""

  REPORT_ATTRS = [aff4_grr.VFSGRRClient.SchemaCls.GetAttribute("GRR client")]
  REPORT_NAME = "GRR Client Version Breakdown Report"

  def Run(self, max_age=60 * 60 * 24 * 7):
    """Run the report."""
    counts = {}
    self.fields.append("count")
    self.results = []
    for client in self._QueryResults(max_age):
      version = client.get("GRR client")
      try:
        counts[version] += 1
      except KeyError:
        counts[version] = 1
    for version, count in counts.iteritems():
      self.results.append({"GRR client": version, "count": count})
    self.SortResults("count")


class ClientReportIterator(export_utils.IterateAllClients):
  """Iterate through all clients generating basic client information."""

  def __init__(self, report_attrs, extended_report_attrs, **kwargs):
    """Initialize.

    Args:
      report_attrs: Attributes to retrieve.
      extended_report_attrs: Path, Attribute tuples to retrieve.
      **kwargs: Additional args to fall through to client iterator.
    """
    super(ClientReportIterator, self).__init__(**kwargs)
    self.report_attrs = report_attrs
    self.extended_report_attrs = extended_report_attrs

  def IterFunction(self, client, out_queue, unused_token):
    """Extract report attributes."""
    result = {}
    for attr in self.report_attrs:
      # Do some special formatting for certain fields.
      if attr.name == "subject":
        result[attr.name] = client.Get(attr).Basename()
      elif attr.name == "GRR client":
        c_info = client.Get(attr)
        if not c_info:
          self.broken_subjects.append(client.client_id)
          result[attr.name] = None
          continue

        result[attr.name] = "%s %s" % (c_info.client_name,
                                       str(c_info.client_version))
      else:
        result[attr.name] = client.Get(attr)

    for sub_path, attr in self.extended_report_attrs:
      try:
        client_sub = client.OpenMember(sub_path)
        # TODO(user): Update this to use MultiOpen.
      except IOError:
        # If the path is not found, just continue.
        continue
      # Special case formatting for some attributes.
      if attr.name == "Interfaces":
        interfaces = client_sub.Get(attr)
        if interfaces:
          try:
            result[attr.name] = ",".join(interfaces.GetIPAddresses())
          except AttributeError:
            result[attr.name] = ""
      else:
        result[attr.name] = client_sub.Get(attr)

    out_queue.put(result)


class ReportName(rdfvalue.RDFString):
  """A class for reports we support."""

  type = "ReportName"

  def ParseFromString(self, value):
    super(ReportName, self).ParseFromString(value)
    if value not in Report.classes:
      raise ValueError("Invalid report %s." % value)
