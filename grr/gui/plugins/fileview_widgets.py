#!/usr/bin/env python
"""Widgets for advanced display of files."""



from grr.gui import renderers
from grr.lib import utils


class HexView(renderers.TemplateRenderer):
  """Display a HexView of a file.

  Internal State:
    - aff4_path: The name of the aff4 object we are viewing now.
    - age: The version of the AFF4 object to display.
  """
  table_width = 32
  total_size = 0

  # The state of this widget.
  state = {}

  # This is the template used by the js to build the hex viewer html.
  table_jquery_template = """
<div id="HexTableTemplate">
<table class="monospace">
 <tbody>
  <tr id="hex_header" class="ui-state-default">
   <th id="offset">offset</th>
   <th id="data_column"></th>
  </tr>
  <tr>
   <td id="offset_area">
    <table>
    </table>
   </td>
   <td id="hex_area">
    <table>
    </table>
   </td>
   <td id="data_area" class="data_area">
    <table>
    </table>
   </td>
   <td class='slider_area'><div id=slider></div></td>
  </tr>
</tbody>
</table>
</div>
"""

  layout_template = renderers.Template("""
<div id="{{unique|escape}}" style="position: absolute; top: 45px;
right: 0; bottom: 0; left: 0"></div> """ + table_jquery_template)

  def Layout(self, request, response):
    """Render the content of the tab or the container tabset."""
    self.state["aff4_path"] = request.REQ.get("aff4_path")
    self.state["age"] = request.REQ.get("age")

    response = super(HexView, self).Layout(request, response)
    return self.CallJavascript(response,
                               "HexView.Layout",
                               renderer=self.__class__.__name__,
                               table_width=self.table_width,
                               aff4_path=self.state["aff4_path"],
                               age=self.state["age"])

  def RenderAjax(self, request, response):
    """Return the contents of the hex viewer in JSON."""
    try:
      row_count = int(request.REQ.get("hex_row_count", 10))
    except ValueError:
      row_count = 2

    try:
      offset = int(request.REQ.get("offset", 0))
    except ValueError:
      offset = 0

    data = [
        ord(x)
        for x in self.ReadBuffer(request, offset, row_count * self.table_width)
    ]

    response = dict(offset=offset, values=data)
    response["total_size"] = self.total_size

    return renderers.JsonResponse(dict(offset=offset,
                                       values=data,
                                       total_size=self.total_size))

  def ReadBuffer(self, request, offset, length):
    """Should be overriden by derived classes to satisfy read requests.

    Args:
      request: The original request object.
      offset: The offset inside the file we should read from.
      length: The number of bytes to return.

    Returns:
      An array of integers between 0 and 255 corresponding to the bytes.
    """
    return [x % 255 for x in xrange(offset, offset + length)]


class TextView(renderers.TemplateRenderer):
  """Display a TextView of a file."""
  # The state of this widget.
  state = {}
  total_size = 0
  default_codec = "utf_8"
  allowed_codecs = ["base64_codec", "big5", "big5hkscs", "cp037", "cp1006",
                    "cp1026", "cp1140", "cp1250", "cp1251", "cp1252", "cp1253",
                    "cp1254", "cp1255", "cp1256", "cp1257", "cp1258", "cp424",
                    "cp437", "cp500", "cp737", "cp775", "cp850", "cp852",
                    "cp855", "cp856", "cp857", "cp860", "cp861", "cp862",
                    "cp863", "cp864", "cp865", "cp866", "cp869", "cp874",
                    "cp875", "cp932", "cp949", "cp950"
                    "idna", "rot_13", "utf_16", "utf_16_be", "utf_16_le",
                    "utf_32", "utf_32_be", "utf_32_le", "utf_7", "utf_8",
                    "utf_8_sig", "uu_codec", "zlib_codec"]

  layout_template = renderers.Template("""
<div id="{{unique|escape}}">
<div id="text_viewer">
  offset <input id="text_viewer_offset" name="offset" type=text value=0 size=6>
  size <input id="text_viewer_data_size" name="text_data_size"
        type=text value=0 size=6>

  encoding <select id="text_encoding" name="text_encoding">
  {% for encoder in this.allowed_codecs %}
    <option value={{encoder|escape}}>{{encoder|escape}}</option>
  {% endfor %}
</select>

<div id="text_viewer_slider"></div>
<div id="text_viewer_data" total_size=0>
  <div id="text_viewer_data_content" total_size=0></div>
</div>
</div>
</div>
""")

  action_template = renderers.Template("""
<div id="text_viewer_data_content" total_size="{{this.total_size|escape}}">
{% if this.error %}
  <div class="errormsg">{{this.error|escape}}</div>
{% else %}
<pre class="monospace">
  {{this.data|escape}}
</pre>
{% endif %}
</div>
""")

  def Layout(self, request, response):
    """Render the content of the tab or the container tabset."""
    self.state["aff4_path"] = request.REQ.get("aff4_path")
    self.state["age"] = request.REQ.get("age")

    response = super(TextView, self).Layout(request, response)
    return self.CallJavascript(response,
                               "TextView.Layout",
                               default_codec=self.default_codec,
                               aff4_path=self.state["aff4_path"],
                               age=self.state["age"])

  def RenderAjax(self, request, response):
    """Return the contents of the text viewer."""
    try:
      self.data_size = int(request.REQ.get("data_size", 10000))
      self.offset = int(request.REQ.get("offset", 0))
    except ValueError:
      self.error = "Invalid data_size or offset given."
      return renderers.TemplateRenderer.Layout(self, request, response,
                                               self.action_template)

    text_encoding = request.REQ.get("text_encoding", self.default_codec)
    try:
      buf = self.ReadBuffer(request, self.offset, self.data_size)
      self.data = self._Decode(text_encoding, buf)
    except RuntimeError as e:
      self.error = "Failed to decode: %s" % utils.SmartStr(e)

    return renderers.TemplateRenderer.Layout(self, request, response,
                                             self.action_template)

  def _Decode(self, codec_name, data):
    """Decode data with the given codec name."""
    if codec_name not in self.allowed_codecs:
      raise RuntimeError("Invalid encoding requested.")

    try:
      return data.decode(codec_name, "replace")
    except LookupError:
      raise RuntimeError("Codec could not be found.")
    except AssertionError:
      raise RuntimeError("Codec failed to decode")

  def ReadBuffer(self, request, offset, length):
    """Should be overriden by derived classes to satisfy read requests.

    Args:
      request: The original request object.
      offset: The offset inside the file we should read from.
      length: The number of bytes to return.

    Returns:
      An array of integers between 0 and 255 corresponding to the bytes.
    """
    return "".join(x % 255 for x in xrange(offset, offset + length))
