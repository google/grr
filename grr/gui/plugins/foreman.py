#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-
#
# Copyright 2010 Google Inc. All Rights Reserved.
"""This is the interface for managing the foreman."""


from grr.gui import renderers
from grr.gui.plugins import semantic
from grr.lib import aff4


class RuleArray(semantic.RDFProtoRenderer):
  """Nicely render all the rules."""
  proxy_field = "client_rule_set"


class ActionRuleArray(semantic.RDFValueArrayRenderer):
  """Nicely render all the actions for a rule."""
  proxy_field = "actions"


class ReadOnlyForemanRuleTable(renderers.UserLabelCheckMixin,
                               renderers.TableRenderer):
  """Show all the foreman rules."""
  description = "Automated Flows View"
  behaviours = frozenset(["GeneralAdvanced"])
  AUTHORIZED_LABELS = ["admin"]

  def __init__(self, **kwargs):
    super(ReadOnlyForemanRuleTable, self).__init__(**kwargs)
    self.AddColumn(semantic.RDFValueColumn("Created"))
    self.AddColumn(semantic.RDFValueColumn("Expires"))
    self.AddColumn(semantic.RDFValueColumn("Description"))
    self.AddColumn(semantic.RDFValueColumn(
        "Rules", renderer=RuleArray, width="40%"))
    self.AddColumn(semantic.RDFValueColumn("Actions", width="40%"))

  def RenderAjax(self, request, response):
    """Renders the table."""
    fd = aff4.FACTORY.Open("aff4:/foreman", token=request.token)
    rules = fd.Get(fd.Schema.RULES, [])
    for rule in rules:
      self.AddRow(Created=rule.created,
                  Expires=rule.expires,
                  Description=rule.description,
                  Rules=rule.client_rule_set,
                  Actions=rule.actions)

    # Call our baseclass to actually do the rendering
    return super(ReadOnlyForemanRuleTable, self).RenderAjax(request, response)
