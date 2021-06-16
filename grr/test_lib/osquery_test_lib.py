#!/usr/bin/env python
"""A module with utilities for testing osquery-related code."""

import contextlib
import os
import platform
import stat
import unittest

from typing import ContextManager
from typing import Iterator
from typing import Text

from grr_response_core.lib.util import temp
from grr.test_lib import test_lib


def FakeOsqueryiOutput(stdout: Text, stderr: Text) -> ContextManager[None]:
  """A context manager with osqueryi executable providing fake output."""
  # TODO: Ugly formatting.
  script = """\
#!/usr/bin/env bash
>&2 cat << $EOF$
{stderr}
$EOF$
cat << $EOF$
{stdout}
$EOF$
""".format(
    stdout=stdout, stderr=stderr)
  return _FakeOsqueryiScript(script)


def FakeOsqueryiSleep(time: float) -> ContextManager[None]:
  """A context manager with osqueryi executable hanging for some time."""
  script = """\
#!/usr/bin/env bash
sleep {time}
""".format(time=time)
  return _FakeOsqueryiScript(script)


@contextlib.contextmanager
def _FakeOsqueryiScript(script: Text) -> Iterator[None]:
  """A context manager with fake script pretending to be osqueryi executable."""
  if platform.system() != "Linux":
    raise unittest.SkipTest("Fake osquery scripts are available only on Linux.")

  # We use a temporary directory instead of temporary file because temporary
  # files hold a write lock that makes it impossible to be read by subprocesses.
  with temp.AutoTempDirPath(remove_non_empty=True) as dirpath:
    filepath = os.path.join(dirpath, "__script__")
    with open(filepath, "w", encoding="utf-8") as filedesc:
      filedesc.write(script)

    # Make the file executable.
    st = os.stat(filepath)
    os.chmod(filepath, st.st_mode | stat.S_IEXEC)

    with test_lib.ConfigOverrider({"Osquery.path": filepath}):
      yield
