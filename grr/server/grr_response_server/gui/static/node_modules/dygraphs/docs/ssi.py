'''
Shared code for ssi_server.py and ssi_expander.py.
'''

import re

def InlineIncludes(path):
  """Read a file, expanding <!-- #include --> statements."""
  content = file(path).read()
  content = re.sub(r'<!-- *#include *virtual=[\'"]([^\'"]+)[\'"] *-->',
      lambda x: file(x.group(1)).read(),
      content)
  return content

