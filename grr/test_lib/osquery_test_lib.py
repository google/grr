#!/usr/bin/env python
"""A module with utilities for testing osquery-related code."""
from __future__ import absolute_import
from __future__ import division

from __future__ import unicode_literals

import contextlib
import io
import os
import platform
import stat
import unittest

from typing import ContextManager
from typing import Iterator
from typing import Text

from grr_response_core.lib.util import temp
from grr.test_lib import test_lib


def FakeOsqueryiOutput(output):
  """A context manager with osqueryi executable providing fake output."""
  script = """\
#!/usr/bin/env bash
cat << $EOF$
{output}
$EOF$
""".format(output=output)
  return _FakeOsqueryiScript(script)


def FakeOsqueryiError(error):
  """A context manager with osqueryi executable providing fake error output."""
  script = """\
#!/usr/bin/env bash
>&2 cat << $EOF$
{error}
$EOF$
""".format(error=error)
  return _FakeOsqueryiScript(script)


def FakeOsqueryiSleep(time):
  """A context manager with osqueryi executable hanging for some time."""
  script = """\
#!/usr/bin/env bash
sleep {time}
""".format(time=time)
  return _FakeOsqueryiScript(script)


@contextlib.contextmanager
def _FakeOsqueryiScript(script):
  """A context manager with fake script pretending to be osqueri executable."""
  if platform.system() != "Linux":
    raise unittest.SkipTest("Fake osquery scripts are available only on Linux.")

  # We use a temporary directory instead of temporary file because temporary
  # files hold a write lock that makes it impossible to be read by subprocesses.
  with temp.AutoTempDirPath(remove_non_empty=True) as dirpath:
    filepath = os.path.join(dirpath, "__script__")
    with io.open(filepath, "w") as filedesc:
      filedesc.write(script)

    # Make the file executable.
    st = os.stat(filepath)
    os.chmod(filepath, st.st_mode | stat.S_IEXEC)

    with test_lib.ConfigOverrider({"Osquery.path": filepath}):
      yield
