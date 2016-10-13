#!/usr/bin/env python
"""GUI elements to display general statistics."""


import math
import time

from grr.gui import renderers
from grr.lib import aff4
from grr.lib import rdfvalue
from grr.lib.aff4_objects import aff4_grr
from grr.lib.aff4_objects import stats as aff4_stats


class ShowStatistics(renderers.Splitter2WayVertical):
  """View various statistics."""

  description = "Show Statistics"
  behaviours = frozenset(["General"])

  left_renderer = "StatsTree"
  right_renderer = "ReportRenderer"


def InterpolatePaths(path, labels):
  """Interpolate paths with %%LABEL%% markers.

  Args:
    path: path string to interpolate
    labels: list of label strings
  Returns:
    list of path strings for each label supplied
  """
  if "%%LABEL%%" not in path:
    return dict([(path, None)])
  else:
    paths = {}
    for label in labels:
      paths[path.replace("%%LABEL%%", label)] = label
    return paths


def GetClassLookupDict(classes, labels):
  """Build a path->class lookup dict.

  Args:
    classes: list of class objects
    labels: list of label strings
  Returns:
    Dict of (class object, label string) tuples keyed by path
  """
  paths = {}
  for cls in classes:
    category = getattr(cls, "category", None)
    if category:
      for path, label in InterpolatePaths(category, labels).items():
        paths[path] = (cls, label)
  return paths


class ReportRenderer(renderers.TemplateRenderer):
  """A renderer for Statistic Reports."""

  layout_template = renderers.Template("""
<div class="padded">
  {% if not this.delegated_renderer %}
    <h3>Select a statistic to view.</h3>
  {% endif %}
  <div id="{{unique|escape}}"></div>
</div>
""")

  def Layout(self, request, response):
    """Delegate to a stats renderer if needed."""
    path = request.REQ.get("path", "")

    labels = aff4_grr.GetAllClientLabels(request.token, include_catchall=True)
    # Try and find the correct renderer to use.
    lookup_dict = GetClassLookupDict(self.classes.values(), labels)
    if path in lookup_dict:
      self.delegated_renderer = lookup_dict[path][0]()

      # Tell the renderer which label it should be using
      request.label = lookup_dict[path][1]

      # Render the renderer directly here
      self.delegated_renderer.Layout(request, response)

    response = super(ReportRenderer, self).Layout(request, response)
    return self.CallJavascript(
        response, "ReportRenderer.Layout", renderer=self.__class__.__name__)


class StatsTree(renderers.TreeRenderer):
  """Show all the available reports."""

  def GetStatsPaths(self, request):
    paths = []
    labels = aff4_grr.GetAllClientLabels(request.token, include_catchall=True)
    for cls in self.classes.values():
      if aff4.issubclass(cls, Report) and cls.category:
        paths.extend(InterpolatePaths(cls.category, labels).keys())
    paths.sort()
    return paths

  def RenderBranch(self, path, request):
    """Show all the stats available."""
    for category_name in self.GetStatsPaths(request):
      if category_name.startswith(path):
        elements = filter(None, category_name[len(path):].split("/"))

        # Do not allow duplicates
        if elements and elements[0] in self:
          continue

        if len(elements) > 1:
          self.AddElement(elements[0], "branch")
        elif elements:
          self.AddElement(elements[0], "leaf")


class Report(renderers.TemplateRenderer):
  """This is the base of all Statistic Reports."""
  category = None

  layout_template = renderers.Template("""
<div class="padded">
{% if this.data %}
  <h3>{{this.title|escape}}</h3>
  <div>
  {{this.description|escape}}
  </div>
  <div id="hover_{{unique|escape}}">Hover to show exact numbers.</div>
  <div id="graph_{{unique|escape}}" class="grr_graph"></div>
{% else %}
  <h3>No data Available</h3>
{% endif %}
</div>
""")


class PieChart(Report):
  """Display a pie chart."""

  def Layout(self, request, response):
    response = super(PieChart, self).Layout(request, response)
    return self.CallJavascript(response, "PieChart.Layout", data=self.data)


class OSBreakdown(PieChart):
  category = "/Clients/%%LABEL%%/OS Breakdown/ 1 Day Active"
  title = "Operating system break down."
  description = "OS breakdown for clients that were active in the last day."
  active_day = 1
  attribute = aff4_stats.ClientFleetStats.SchemaCls.OS_HISTOGRAM
  data_urn = rdfvalue.RDFURN("aff4:/stats/ClientFleetStats")

  def Layout(self, request, response):
    """Extract only the operating system type from the active histogram."""
    try:
      fd = aff4.FACTORY.Open(
          self.data_urn.Add(request.label), token=request.token)
      self.data = []
      for graph in fd.Get(self.attribute):
        # Find the correct graph and merge the OS categories together
        if "%s day" % self.active_day in graph.title:
          for sample in graph:
            self.data.append(dict(label=sample.label, data=sample.y_value))
          break
    except (IOError, TypeError):
      pass

    return super(OSBreakdown, self).Layout(request, response)


class OSBreakdown7(OSBreakdown):
  category = "/Clients/%%LABEL%%/OS Breakdown/ 7 Day Active"
  description = "OS breakdown for clients that were active in the last week."
  active_day = 7


class OSBreakdown30(OSBreakdown):
  category = "/Clients/%%LABEL%%/OS Breakdown/30 Day Active"
  description = "OS breakdown for clients that were active in the last month."
  active_day = 30


class ReleaseBreakdown(OSBreakdown):
  category = "/Clients/%%LABEL%%/OS Release Breakdown/ 1 Day Active"
  title = "Operating system version break down."
  description = "This plot shows what OS clients active within the last day."
  active_day = 1
  attribute = aff4_stats.ClientFleetStats.SchemaCls.RELEASE_HISTOGRAM


class ReleaseBreakdown7(ReleaseBreakdown):
  category = "/Clients/%%LABEL%%/OS Release Breakdown/ 7 Day Active"
  description = "What OS Version clients were active within the last week."
  active_day = 7


class ReleaseBreakdown30(ReleaseBreakdown):
  category = "/Clients/%%LABEL%%/OS Release Breakdown/30 Day Active"
  description = "What OS Version clients were active within the last month."
  active_day = 30


class LastActiveReport(Report):
  """Display a histogram of last actives."""
  category = "/Clients/%%LABEL%%/Last Active/Count of last activity time"
  title = "Breakdown of Client Count Based on Last Activity of the Client."
  description = """
This plot shows the number of clients active in the last day and how that number
evolves over time.
"""
  active_days_display = [1, 3, 7, 30, 60]
  attribute = aff4_stats.ClientFleetStats.SchemaCls.LAST_CONTACTED_HISTOGRAM
  data_urn = rdfvalue.RDFURN("aff4:/stats/ClientFleetStats")

  layout_template = renderers.Template("""
<div class="padded">
{% if this.graphs %}
  <h3>{{this.title|escape}}</h3>
  <div id="{{unique|escape}}_click">
    {{this.description|escape}}
  </div>
  <div id="{{unique|escape}}" class="grr_graph"></div>
{% else %}
  <h3>No data Available</h3>
{% endif %}
</div>
""")

  def _ProcessGraphSeries(self, graph_series):
    for graph in graph_series:
      for sample in graph:
        # Provide the time in js timestamps (millisecond since the epoch)
        days = sample.x_value / 1000000 / 24 / 60 / 60
        if days in self.active_days_display:
          label = "%s day active" % days
          self.categories.setdefault(label, []).append(
              (graph_series.age / 1000, sample.y_value))

  def Layout(self, request, response):
    """Show how the last active breakdown evolves over time."""
    try:
      self.start_time, self.end_time = GetAgeTupleFromRequest(request, 180)
      fd = aff4.FACTORY.Open(
          self.data_urn.Add(request.label),
          token=request.token,
          age=(self.start_time, self.end_time))
      self.categories = {}
      for graph_series in fd.GetValuesForAttribute(self.attribute):
        self._ProcessGraphSeries(graph_series)

      self.graphs = []
      for k, v in self.categories.items():
        graph = dict(label=k, data=v)
        self.graphs.append(graph)
    except IOError:
      pass

    response = super(LastActiveReport, self).Layout(request, response)
    return self.CallJavascript(
        response, "LastActiveReport.Layout", graphs=self.graphs)


class LastDayGRRVersionReport(LastActiveReport):
  """Display a histogram of last actives based on GRR Version."""
  category = "/Clients/%%LABEL%%/GRR Version/ 1 Day"
  title = "1 day Active Clients."
  description = """This shows the number of clients active in the last day based
on the GRR version.
"""
  active_day = 1
  attribute = aff4_stats.ClientFleetStats.SchemaCls.GRRVERSION_HISTOGRAM

  def _ProcessGraphSeries(self, graph_series):
    for graph in graph_series:
      # Find the correct graph and merge the OS categories together
      if "%s day" % self.active_day in graph.title:
        for sample in graph:
          self.categories.setdefault(sample.label, []).append(
              (graph_series.age / 1000, sample.y_value))
        break


class Last7DaysGRRVersionReport(LastDayGRRVersionReport):
  """Display a histogram of last actives based on GRR Version."""
  category = "/Clients/%%LABEL%%/GRR Version/ 7 Day"
  title = "7 day Active Clients."
  description = """This shows the number of clients active in the last 7 days
based on the GRR version.
"""
  active_day = 7


class Last30DaysGRRVersionReport(LastDayGRRVersionReport):
  """Display a histogram of last actives based on GRR Version."""
  category = "/Clients/%%LABEL%%/GRR Version/ 30 Day"
  title = "30 day Active Clients."
  description = """This shows the number of clients active in the last 30 days
based on the GRR version.
"""
  active_day = 30


class StatGraph(object):
  """Class for building display graphs."""

  def __init__(self, name, graph_id, click_text):
    self.series = []
    self.click_text = click_text
    self.id = graph_id
    self.name = name

  def AddSeries(self, series, series_name, max_samples=1000):
    """Add a downsampled series to a graph."""
    downsample_ratio = 1
    if max_samples and series:
      downsample_ratio = int(math.ceil(float(len(series)) / max_samples))
    data = [[k, series[k]] for k in sorted(series)[::downsample_ratio]]
    self.series.append(StatData(series_name, data))
    self.downsample = downsample_ratio

  def ToDict(self):
    return dict(self.__dict__, series=[s.ToDict() for s in self.series])


class StatData(object):

  def __init__(self, label, data):
    self.data = data
    self.label = label

  def ToDict(self):
    return self.__dict__


def GetAgeTupleFromRequest(request, default_days=90):
  """Check the request for start/end times and return aff4 age tuple."""
  now = int(time.time() * 1e6)
  default_start = now - (60 * 60 * 24 * 1e6 * default_days)
  start_time = int(request.REQ.get("start_time", default_start))
  end_time = int(request.REQ.get("end_time", now))
  return (start_time, end_time)


class CustomXAxisChart(Report):
  """Bar chart with custom ticks on X axis."""

  def FormatLabel(self, value):
    return str(value)

  def Layout(self, request, response):
    """Set X,Y values."""
    try:
      fd = aff4.FACTORY.Open(self.data_urn, token=request.token)
      self.graph = fd.Get(self.attribute)

      self.data = []
      self.xaxis_ticks = []
      if self.graph:
        for point in self.graph.data:
          self.data.append([[point.x_value, point.y_value]])
          self.xaxis_ticks.append(
              [point.x_value, self.FormatLabel(point.x_value)])

    except (IOError, TypeError):
      pass

    response = super(CustomXAxisChart, self).Layout(request, response)
    return self.CallJavascript(
        response,
        "CustomXAxisChart.Layout",
        data=self.data,
        xaxis_ticks=self.xaxis_ticks)


class LogXAxisChart(CustomXAxisChart):
  """Chart with a log10 x axis.

  Workaround for buggy log scale display in flot:
    https://code.google.com/p/flot/issues/detail?id=26
  """

  def Layout(self, request, response):
    try:
      fd = aff4.FACTORY.Open(self.data_urn, token=request.token)
      self.graph = fd.Get(self.attribute)

      self.data = []
      self.xaxis_ticks = []
      if self.graph:
        for point in self.graph.data:
          # Note 0 and 1 are collapsed into a single category
          if point.x_value > 0:
            x_value = math.log10(point.x_value)
          else:
            x_value = point.x_value
          self.data.append([[x_value, point.y_value]])
          self.xaxis_ticks.append([x_value, self.FormatLabel(point.x_value)])

    except (IOError, TypeError):
      pass

    response = super(CustomXAxisChart, self).Layout(request, response)
    return self.CallJavascript(
        response,
        "CustomXAxisChart.Layout",
        data=self.data,
        xaxis_ticks=self.xaxis_ticks)


class FileStoreFileTypes(PieChart):
  title = "Filetypes stored in filestore."
  description = ""
  category = "/FileStore/FileTypes"
  attribute = aff4_stats.FilestoreStats.SchemaCls.FILESTORE_FILETYPES

  def Layout(self, request, response):
    """Extract only the operating system type from the active histogram."""
    try:
      fd = aff4.FACTORY.Open("aff4:/stats/FileStoreStats", token=request.token)
      self.graph = fd.Get(self.attribute)

      self.data = []
      for sample in self.graph:
        self.data.append(dict(label=sample.label, data=sample.y_value))
    except (IOError, TypeError):
      pass

    return super(FileStoreFileTypes, self).Layout(request, response)


class FileStoreSizeFileTypes(FileStoreFileTypes):
  title = "Total filesize in GB of files in the filestore by type."
  description = ""
  category = "/FileStore/TotalFileSize"
  attribute = aff4_stats.FilestoreStats.SchemaCls.FILESTORE_FILETYPES_SIZE


def SizeToReadableString(filesize):
  """Turn a filesize int into a human readable filesize.

  From http://stackoverflow.com/questions/1094841/

  Args:
    filesize: int
  Returns:
    string: human readable size representation.
  """
  for x in ["bytes", "KiB", "MiB", "GiB", "TiB"]:
    if filesize < 1000.0:
      return "%3.1f %s" % (filesize, x)
    filesize /= 1000.0


class FileStoreFileSizes(LogXAxisChart):
  title = "Number of files in filestore by size"
  description = "X: log10 (filesize), Y: Number of files"
  category = "/FileStore/FileSizeDistribution"
  data_urn = "aff4:/stats/FileStoreStats"
  attribute = aff4_stats.FilestoreStats.SchemaCls.FILESTORE_FILESIZE_HISTOGRAM

  def FormatLabel(self, value):
    return SizeToReadableString(value)


class FileClientCount(CustomXAxisChart):
  title = "File frequency by client count."
  description = ("Number of files seen on 0, 1, 5 etc. clients. X: number of"
                 " clients, Y: number of files.")
  category = "/FileStore/ClientCounts"
  data_urn = "aff4:/stats/FileStoreStats"
  attribute = (
      aff4_stats.FilestoreStats.SchemaCls.FILESTORE_CLIENTCOUNT_HISTOGRAM)
