#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-
#
"""This plugin renders the filesystem in a tree and a table."""


import os

from django import http

from grr.gui import renderers
from grr.lib import aff4
from grr.lib import config_lib
from grr.lib import rdfvalue
from grr.lib import utils


class DownloadView(renderers.TemplateRenderer):
  """Renders a download page."""

  # We allow a longer execution time here to be able to download large files.
  max_execution_time = 60 * 15

  layout_template = renderers.Template("""
<h3>{{ this.path|escape }}</h3>
<div id="{{ unique|escape }}_action" class="hide"></div>
{% if this.hash %}
Hash was {{ this.hash|escape }}.
{% endif %}

{% if this.file_exists %}
As downloaded on {{ this.age|escape }}.<br>
<p>
<button id="{{ unique|escape }}_2" class="btn btn-default">
 Download ({{this.size|escape}} bytes)
</button>
</p>
<p>or download using command line export tool:</p>
<pre>
{{ this.export_command_str|escape }}
</pre>
<hr/>
{% endif %}
<button id="{{ unique|escape }}" class="btn btn-default">
  Get a new Version
</button>
</div>
""")

  error_template = renderers.Template("""
<div class="alert alert-danger alert-block">
  <h4>Error!</h4> {{this.path|escape}} does not appear to be a file object.
  <p><em>{{this.error_message|escape}}</em></p>
</div>
""")
  bad_extensions = [
      ".bat", ".cmd", ".exe", ".com", ".pif", ".py", ".pl", ".scr", ".vbs"
  ]

  def Layout(self, request, response):
    """Present a download form."""
    self.age = rdfvalue.RDFDatetime(request.REQ.get("age"))

    client_id = request.REQ.get("client_id")
    aff4_path = request.REQ.get("aff4_path", client_id)

    try:
      fd = aff4.FACTORY.Open(aff4_path, token=request.token, age=self.age)
      self.path = fd.urn
      self.hash = fd.Get(fd.Schema.HASH, None)
      self.size = fd.Get(fd.Schema.SIZE)

      # If data is available to read - we present the download button.
      self.file_exists = False
      try:
        if fd.Read(1):
          self.file_exists = True
      except (IOError, AttributeError):
        pass

      self.export_command_str = u" ".join([
          config_lib.CONFIG["AdminUI.export_command"], "--username",
          utils.ShellQuote(request.token.username), "file", "--path",
          utils.ShellQuote(aff4_path), "--output", "."
      ])

      response = super(DownloadView, self).Layout(request, response)
      return self.CallJavascript(
          response,
          "DownloadView.Layout",
          aff4_path=aff4_path,
          client_id=client_id,
          age_int=int(self.age),
          file_exists=self.file_exists,
          renderer=self.__class__.__name__,
          reason=request.token.reason)
    except (AttributeError, IOError) as e:
      # Render the error template instead.
      self.error_message = e.message
      return renderers.TemplateRenderer.Layout(self, request, response,
                                               self.error_template)

  def Download(self, request, _):
    """Stream the file into the browser."""
    # Open the client
    client_id = request.REQ.get("client_id")
    self.aff4_path = request.REQ.get("aff4_path", client_id)
    self.age = rdfvalue.RDFDatetime(request.REQ.get("age")) or aff4.NEWEST_TIME
    self.token = request.token
    # If set, we don't append .noexec to dangerous extensions.
    safe_extension = bool(request.REQ.get("safe_extension", 0))

    if self.aff4_path:

      def Generator():
        fd = aff4.FACTORY.Open(
            self.aff4_path, token=request.token, age=self.age)

        while True:
          data = fd.Read(1000000)
          if not data:
            break

          yield data

      filename = os.path.basename(utils.SmartStr(self.aff4_path))
      if not safe_extension:
        for ext in self.bad_extensions:
          if filename.lower().endswith(ext):
            filename += ".noexec"

      response = http.StreamingHttpResponse(
          streaming_content=Generator(), content_type="binary/octet-stream")
      # This must be a string.
      response["Content-Disposition"] = ("attachment; filename=%s" % filename)

      return response
