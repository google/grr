#!/usr/bin/env python
"""IPython extension for GRR Colab library."""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from grr_colab import magics


def load_ipython_extension(ipython):
  register_magic_functions(ipython)


def unload_ipython_extension(ipython):
  del ipython  # Unused.


def register_magic_functions(ipython):
  """Registers GRR Colab magic functions.

  Args:
    ipython: Currently active InteractiveShell instance.

  Returns:
    Nothing.
  """
  ipython.register_magic_function(magics.grr_set_no_flow_timeout)
  ipython.register_magic_function(magics.grr_set_default_flow_timeout)
  ipython.register_magic_function(magics.grr_set_flow_timeout)
  ipython.register_magic_function(magics.grr_list_artifacts)
  ipython.register_magic_function(magics.grr_search_clients)
  ipython.register_magic_function(magics.grr_search_online_clients)
  ipython.register_magic_function(magics.grr_set_client)
  ipython.register_magic_function(magics.grr_request_approval)
  ipython.register_magic_function(magics.grr_id)
  ipython.register_magic_function(magics.grr_cd)
  ipython.register_magic_function(magics.grr_pwd)
  ipython.register_magic_function(magics.grr_ls)
  ipython.register_magic_function(magics.grr_stat)
  ipython.register_magic_function(magics.grr_head)
  ipython.register_magic_function(magics.grr_grep)
  ipython.register_magic_function(magics.grr_fgrep)
  ipython.register_magic_function(magics.grr_interrogate)
  ipython.register_magic_function(magics.grr_hostname)
  ipython.register_magic_function(magics.grr_ifconfig)
  ipython.register_magic_function(magics.grr_uname)
  ipython.register_magic_function(magics.grr_ps)
  ipython.register_magic_function(magics.grr_osqueryi)
  ipython.register_magic_function(magics.grr_collect)
  ipython.register_magic_function(magics.grr_yara)
  ipython.register_magic_function(magics.grr_wget)
