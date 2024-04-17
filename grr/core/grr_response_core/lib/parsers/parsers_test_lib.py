#!/usr/bin/env python
"""Parser testing lib."""

import io

from grr_response_core.lib.rdfvalues import client_fs as rdf_client_fs
from grr_response_core.lib.rdfvalues import paths as rdf_paths


def GenInit(svc, desc, start=("2", "3", "4", "5"), stop="1"):
  """Generate init file."""
  insserv = r"""
    $local_fs   +umountfs
    $network    +networking
    $remote_fs  $local_fs +umountnfs +sendsigs
    $syslog     +rsyslog +sysklogd +syslog-ng +dsyslog +inetutils-syslogd
    """
  tmpl = r"""
    ### BEGIN INIT INFO
    # Provides:             %s
    # Required-Start:       $remote_fs $syslog
    # Required-Stop:        $syslog
    # Default-Start:        %s
    # Default-Stop:         %s
    # Short-Description:    %s
    ### END INIT INFO
    """ % (svc, " ".join(start), " ".join(stop), desc)
  return {
      "/etc/insserv.conf": insserv.encode("utf-8"),
      "/etc/init.d/%s" % svc: tmpl.encode("utf-8"),
  }


def GenTestData(paths, data, st_mode=33188):
  stats = []
  files = []
  for path in paths:
    p = rdf_paths.PathSpec(path=path, pathtype="OS")
    stats.append(rdf_client_fs.StatEntry(pathspec=p, st_mode=st_mode))
  for val in data:
    files.append(io.BytesIO(val.encode("utf-8")))
  return stats, files


def GenXinetd(svc="test", disable="no"):
  """Generate xinetd file."""
  defaults = r"""
    defaults
    {
       instances      = 60
       log_type       = SYSLOG     authpriv
       log_on_success = HOST PID
       log_on_failure = HOST
       cps            = 25 30
    }
    includedir /etc/xinetd.d
    """.encode("utf-8")
  tmpl = ("""
    service %s
    {
       disable         = %s
    }
    """ % (svc, disable)).encode("utf-8")
  return {"/etc/xinetd.conf": defaults, "/etc/xinetd.d/%s" % svc: tmpl}
