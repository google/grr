#!/usr/bin/python
'''
Use this in the same way as Python's SimpleHTTPServer:

  ./ssi_server.py [port]

The only difference is that, for files ending in '.html', ssi_server will
inline SSI (Server Side Includes) of the form:

  <!-- #include virtual="fragment.html" -->

Run ./ssi_server.py in this directory and visit localhost:8000 for an exmaple.
'''

import os
import ssi
from SimpleHTTPServer import SimpleHTTPRequestHandler
import SimpleHTTPServer
import tempfile


class SSIRequestHandler(SimpleHTTPRequestHandler):
  """Adds minimal support for <!-- #include --> directives.
  
  The key bit is translate_path, which intercepts requests and serves them
  using a temporary file which inlines the #includes.
  """

  def __init__(self, request, client_address, server):
    self.temp_files = []
    SimpleHTTPRequestHandler.__init__(self, request, client_address, server)

  def do_GET(self):
    SimpleHTTPRequestHandler.do_GET(self)
    self.delete_temp_files()

  def do_HEAD(self):
    SimpleHTTPRequestHandler.do_HEAD(self)
    self.delete_temp_files()

  def translate_path(self, path):
    fs_path = SimpleHTTPRequestHandler.translate_path(self, path)
    if self.path.endswith('/'):
      for index in "index.html", "index.htm":
        index = os.path.join(fs_path, index)
        if os.path.exists(index):
          fs_path = index
          break

    if fs_path.endswith('.html'):
      content = ssi.InlineIncludes(fs_path)
      fs_path = self.create_temp_file(fs_path, content)
    return fs_path

  def delete_temp_files(self):
    for temp_file in self.temp_files:
      os.remove(temp_file)

  def create_temp_file(self, original_path, content):
    _, ext = os.path.splitext(original_path)
    fd, path = tempfile.mkstemp(suffix=ext)
    os.write(fd, content)
    os.close(fd)

    self.temp_files.append(path)
    return path


if __name__ == '__main__':
  SimpleHTTPServer.test(HandlerClass=SSIRequestHandler)
