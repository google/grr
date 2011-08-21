#!/usr/bin/env python
#
# Copyright 2010 Google Inc.
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


"""This plugin renders the client search page."""

from django import template
from grr.gui import renderers
from grr.lib import aff4


class ContentView(renderers.Renderer):
  """Manage the main content pane."""

  template = template.Template("""
<div id="menu" title="Menu"></div>
<div id="main"></div>
<script>
  grr.extruder("Menu", "extruder");

  $(window).bind("resize", function () {
    grr.fixHeight($("#content"));
  }).resize();

  grr.subscribe("extruder", function(renderer) {
    grr.layout(renderer, "main");
    grr.publish("hash_state", "main", renderer);
  }, "main");

  if (grr.hash.c) {
    grr.state.client_id = grr.hash.c;
  };

  // Update main's state from the hash
  if (grr.hash.main) {
    grr.layout(grr.hash.main, "main");
  } else {
    grr.layout("FrontPage", "main");
  };
</script>
""")

  def Layout(self, request, response):
    """Manage content pane depending on passed in query parameter."""
    response = super(ContentView, self).Layout(request, response)

    return self.RenderFromTemplate(
        self.template, response)


class Menu(renderers.Renderer):
  """A Renderer to show all menu options in an extruder."""

  layout_template = template.Template("""
{% for i in categories %}
<div class="voice {panel:'render/RenderAjax/{{ renderer }}?category={{ i }}'}">
  <div class="label" href="components.html">{{ i }}</div>
</div>
{% endfor %}
""")

  ajax_template = template.Template("""
{% for name, description in renderers %}
<div>
  <a class="label" onclick="grr.publish('extruder', '{{ name }}');">
   {{ description }}</a>
</div>
{% endfor %}
""")

  def Layout(self, request, response):
    """Manage content pane depending on passed in query parameter."""
    response = super(Menu, self).Layout(request, response)

    # Introspect all the categories
    categories = set()

    for cls in self.classes.values():
      # Make sure this attribute is defined in the actual class and
      # not in derived classes.
      if "category" in cls.__dict__ and cls.category is not None:
        categories.add(cls.category)

    return self.RenderFromTemplate(
        self.layout_template, response,
        categories=categories,
        renderer=self.__class__.__name__,
        id=self.id
        )

  def RenderAjax(self, request, response):
    """Update the progress bar based on the progress reported."""
    response = super(Menu, self).RenderAjax(request, response)

    # This one is obtained from a href link:
    category = request.GET.get("category")

    # Introspect all the renderers of the given category
    renderer_info = set()

    for name, cls in self.classes.items():
      # Make sure this attribute is defined in the actual class and
      # not in derived classes.
      if "category" in cls.__dict__ and category == cls.category:
        renderer_info.add((name, cls.description))

    return self.RenderFromTemplate(
        self.ajax_template, response,
        renderers=renderer_info,
        renderer=self.__class__.__name__,
        id=self.id
        )


class HostSearch(renderers.TextInput):
  text = "HostName"
  name = "Host"
  publish_queue = "Host"


class OSVersionSearch(renderers.TextInput):
  text = "OS Version:"
  name = "Version"
  publish_queue = "Version"


class MACSearch(renderers.TextInput):
  text = "MAC:"
  name = "MAC"
  publish_queue = "MAC"


class HostTable(renderers.TableRenderer):
  """Render a table for searching hosts."""

  # Update the table if any messages appear in these queues:
  vfs_table_template = template.Template("""<script>
     grr.subscribeUpdateTable("{{ unique|escapejs }}", "Host", "Host");
     grr.subscribeUpdateTable("{{ unique|escapejs }}", "Version",
                              "Version");
     grr.subscribeUpdateTable("{{ unique|escapejs }}", "MAC", "MAC");

     //Receive the selection event and emit a client_id
     grr.subscribe("table_selection_{{ id|escapejs }}", function(node) {
          var spans = node.find("span[type=subject]");
          var cn = $(spans[0]).text();
          var hostname = $(spans[1]).text();
          grr.publish("selection_publish_queue", cn, hostname);
          grr.state.client_id = cn;
     }, "table_{{ unique }}");

    // Delay the focus event to prevent spurious blurring.
    setTimeout(function() {
      $("input[name=Host]").focus();
    }, 500);
  </script>""")

  def __init__(self):
    renderers.TableRenderer.__init__(self)
    self.AddColumn(renderers.AttributeColumn("subject"))
    self.AddColumn(renderers.AttributeColumn(
        "Host", renderer=renderers.SubjectRenderer, header=HostSearch()))
    self.AddColumn(renderers.AttributeColumn(
        "Version", header=OSVersionSearch()))
    self.AddColumn(renderers.AttributeColumn(
        "MAC", header=MACSearch()))
    self.AddColumn(renderers.AttributeColumn("Install"))
    self.AddColumn(renderers.AttributeColumn("Clock"))

  def Layout(self, request, response):
    response = super(HostTable, self).Layout(request, response)

    return self.RenderFromTemplate(
        self.vfs_table_template,
        response,
        event_queue=self.event_queue,
        unique=self.unique, id=self.id)

  def RenderAjax(self, request, response):
    """Draw table cells."""
    start = int(request.REQ.get("iDisplayStart", 0))
    length = int(request.REQ.get("iDisplayLength", 10))
    row_count = 0

    filter_conditions = ["type = VFSGRRClient"]
    for i in ["Host", "Version", "MAC"]:
      value = request.REQ.get(i)
      if value:
        filter_conditions.append("%s contains '%s'" % (
            i, value.replace("'", "\\'")))

    filter_expression = " and ".join(filter_conditions)

    if len(filter_conditions) > 1:
      for child in aff4.FACTORY.root.Query(filter_expression):
        index = start + row_count

        # Add the fd to all the columns
        for column in self.columns:
          try:
            column.AddRowFromFd(index, child)
          except AttributeError: pass

        row_count += 1
        self.size = max(self.size, row_count)

        if row_count > length: break

    # Call our baseclass to actually do the rendering
    return renderers.TableRenderer.RenderAjax(self, request, response)


class SearchHostView(renderers.Renderer):
  """Show a search screen for the host."""

  title = "Search Client"

  template = template.Template("""
<button id="select_button" title='Select Host'>{{ title }}</button>
<div id="search_host_view"></div>
<script>
 $('#select_button').button();
 grr.dialog("HostTable", "search_host_view", "select_button");
 grr.subscribe("selection_publish_queue", function (cn, hostname) {
   $('#search_host_view').dialog('close');
   $('#select_button').text(hostname);
   grr.state.client_id = cn;
   grr.publish("client_selection", cn, hostname);
   grr.publish("hash_state", "c", cn);
   grr.publish("hash_state", "h", hostname);
 }, "select_button");

 /* If the hash is set - send a client_selection event */
 if (grr.hash.h) {
   grr.publish("selection_publish_queue", grr.hash.c, grr.hash.h);
 };

</script>
""")

  def Layout(self, request, response):
    """Display a search screen for the host."""
    response = super(SearchHostView, self).Layout(request, response)

    return self.RenderFromTemplate(
        self.template, response, title=self.title,
        id=self.id)


class FrontPage(renderers.Renderer):
  """The front page of the GRR application."""

  layout_template = template.Template("""
<div id='front'><h1>Welcome to GRR</h1></div>
<script>
 $('#select_button').click();

 grr.subscribe("selection_publish_queue", function (cn, hostname) {
   grr.publish("hash_state", "main", "VirtualFileSystemView");
   grr.layout("VirtualFileSystemView", "main");
 }, "front");
</script>
""")

  def Layout(self, request, response):
    """Manage content pane depending on passed in query parameter."""
    response = super(FrontPage, self).Layout(request, response)

    return self.RenderFromTemplate(
        self.layout_template, response)
