#!/usr/bin/env python
"""The MySQL database methods for handling artifacts."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals


class MySQLDBArtifactsMixin(object):
  """An MySQL database mixin with artifact-related methods."""

  def WriteArtifact(self, artifact):
    raise NotImplementedError()

  def ReadArtifact(self, name):
    raise NotImplementedError()

  def ReadAllArtifacts(self):
    raise NotImplementedError()

  def DeleteArtifact(self, name):
    raise NotImplementedError()
