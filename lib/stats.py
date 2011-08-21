#!/usr/bin/env python

# Copyright 2011 Google Inc.
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


"""Functions for audit and logging."""



from grr.client import conf as flags
FLAGS = flags.FLAGS


class CountingException(Exception):
  """Each time this exception is raised we increment the counter."""
  # Override with the name of the counter
  counter = None

  def __init__(self, *args, **kwargs):
    if self.counter:
      setattr(STATS, self.counter, getattr(STATS, self.counter) + 1)
    Exception.__init__(self, *args, **kwargs)


class Varz(object):
  """This class keeps tabs on stats."""

  def __getattr__(self, attr):
    # Initialize attributes to 0 if not initialized
    if attr not in self.__dict__:
      setattr(self, attr, 0)

    return self.__dict__[attr]


# A global store of statistics
STATS = Varz()
