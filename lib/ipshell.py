#!/usr/bin/env python

# Copyright 2012 Google Inc.
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


"""A compatibility layer for the IPython shell."""




def IPShell(argv=None, user_ns=None, banner=None):
  if argv is None:
    argv = []

  try:
    from IPython.frontend.terminal.embed import InteractiveShellEmbed
    from IPython.config.loader import Config

    cfg = Config()
    cfg.InteractiveShellEmbed.autocall = 2

    shell = InteractiveShellEmbed(config=cfg, user_ns=user_ns,
                                  banner2=banner)
    shell(local_ns=user_ns)
  except ImportError:
    from IPython import Shell

    # IPython < 0.11
    Shell.IPShell(argv=argv, user_ns=user_ns).mainloop(banner=banner)
