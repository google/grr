#!/usr/bin/env python
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

"""Actions required for CA enrolment."""



from grr.client import actions
from grr.client import conf

FLAGS = conf.PARSER.flags


class SaveCert(actions.ActionPlugin):
  """Accepts a signed certificate from the server and saves it to disk."""

  def Run(self, args):
    """Receive the certificate and store it to disk."""
    # We dont really care about the certificate any more. The ca_enroller flow
    # is changed to not issue this client action now.
