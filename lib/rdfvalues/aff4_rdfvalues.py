#!/usr/bin/env python
"""AFF4-related RDFValues implementations."""



import re

from grr.lib import type_info
from grr.lib import utils

from grr.lib.rdfvalues import structs

from grr.proto import jobs_pb2


class AFF4ObjectLabel(structs.RDFProtoStruct):
  """Labels are used to tag AFF4Objects."""
  protobuf = jobs_pb2.AFF4ObjectLabel

  def __init__(self, initializer=None, age=None, **kwargs):
    super(AFF4ObjectLabel, self).__init__(initializer=initializer,
                                          age=age, **kwargs)

    if initializer is None and "name" in kwargs:
      self.Validate()

  def Validate(self):
    super(AFF4ObjectLabel, self).Validate()

    if not re.match("^[\\w./:\\-]+$", self.name):
      raise type_info.TypeValueError("Label name can only contain: "
                                     "a-zA-Z0-9_./:-, but got: %s" % self.name)

    if not self.owner:
      raise type_info.TypeValueError("Label has to have an owner set.")


class AFF4ObjectLabelsList(structs.RDFProtoStruct):
  """List of AFF4ObjectLabels."""

  protobuf = jobs_pb2.AFF4ObjectLabelsList

  @staticmethod
  def RegexForStringifiedValueMatch(label_name):
    return "(.+,|\\A)%s(,.+|\\Z)" % re.escape(label_name)

  def __str__(self):
    return utils.SmartStr(",".join(self.names))

  def __getitem__(self, item):
    return self.labels[item]

  def __len__(self):
    return len(self.labels)

  def __iter__(self):
    for label in self.labels:
      yield label

  def __nonzero__(self):
    return bool(self.labels)

  @property
  def names(self):
    return sorted(set([label.name for label in self.labels]))

  def HasLabelWithName(self, name):
    return name in self.names

  def AddLabel(self, label):
    if not self.HasLabelWithNameAndOwner(label.name, label.owner):
      self.labels.append(label)
      return True
    else:
      return False

  def RemoveLabel(self, label_to_remove):
    new_labels = []
    for label in self.labels:
      if (label.name == label_to_remove.name and
          label.owner == label_to_remove.owner):
        continue
      new_labels.append(label)

    self.labels = new_labels

  def HasLabelWithNameAndOwner(self, name, owner):
    for l in self.labels:
      if l.name == name and l.owner == owner:
        return True

    return False
