#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-
#
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


"""This is the interface for managing the foreman."""


import json
import time

from django import template
from grr.gui import renderers
from grr.gui.plugins import flow_management
from grr.lib import aff4
from grr.lib import flow
from grr.lib import utils
from grr.proto import jobs_pb2


class ManageForeman(renderers.Splitter2Way):
  """Manages class based flow creation."""
  category = "Flow Management"
  description = "Automated flow scheduling"

  top_renderer = "ForemanRuleTable"
  bottom_renderer = "Empty"


class RegexRuleArray(renderers.RDFProtoArrayRenderer):
  """Nicely render all the rules."""
  proxy_field = "regex_rules"


class ActionRuleArray(renderers.RDFProtoArrayRenderer):
  """Nicely render all the actions for a rule."""
  proxy_field = "actions"

  translator = dict(argv=renderers.RDFProtoRenderer.ProtoDict)


class ForemanRuleTable(renderers.TableRenderer):
  """Show all existing rules."""
  selection_publish_queue = "rule_select"
  table_options = {
      "table_hash": "fr",
      }

  flow_table_template = template.Template("""
<script>
  //Receive the selection event and emit the rule creation time.
  grr.subscribe("table_selection_{{ id|escapejs }}", function(node) {
    if (node) {
      var row_id = node.attr("row_id");
      grr.layout("AddForemanRule", "main_bottomPane", {rule_id: row_id});
      grr.publish("{{ selection_publish_queue|escapejs }}", row_id);
    };
  }, 'table_{{ unique }}');

  grr.layout("ForemanToolbar", "toolbar_{{unique}}", "table_{{unique}}");
</script>
""")

  def __init__(self):
    super(ForemanRuleTable, self).__init__()
    self.AddColumn(renderers.RDFValueColumn("Created"))
    self.AddColumn(renderers.RDFValueColumn("Expires"))
    self.AddColumn(renderers.RDFValueColumn("Description"))
    self.AddColumn(renderers.RDFValueColumn(
        "Rules", renderer=RegexRuleArray))
    self.AddColumn(renderers.RDFValueColumn(
        "Actions", renderer=ActionRuleArray))

  def Layout(self, request, response):
    """The table lists files in the directory and allows file selection."""
    response = super(ForemanRuleTable, self).Layout(request, response)

    return self.RenderFromTemplate(
        self.flow_table_template, response,
        id=self.id, unique=self.unique,
        selection_publish_queue=self.selection_publish_queue,
        )

  def RenderAjax(self, request, response):
    """Renders the table."""
    fd = aff4.FACTORY.Open("aff4:/foreman")
    rules = fd.Get(fd.Schema.RULES)
    if rules is not None:
      for rule in rules:
        self.AddRow(dict(Created=aff4.RDFDatetime(rule.created),
                         Expires=aff4.RDFDatetime(rule.expires),
                         Description=rule.description,
                         Rules=rule,
                         Actions=rule))

    # Call our baseclass to actually do the rendering
    return super(ForemanRuleTable, self).RenderAjax(request, response)


class ForemanToolbar(renderers.Renderer):
  """Renders the toolbar."""

  template = template.Template("""
<button id="add_rule" title="Add a new rule.">
  <img src="/static/images/new.png" class="toolbar_icon">
</button>
<script>
  $("#add_rule").button().click(function () {
     grr.layout("AddForemanRule", "main_bottomPane");
  });
</script>
""")

  def Layout(self, request, response):
    """Render the toolbar."""
    response = super(ForemanToolbar, self).Layout(request, response)

    return self.RenderFromTemplate(self.template, response)


class AddForemanRule(flow_management.FlowInformation):
  """Present a form to add a new rule."""

  layout_template = template.Template("""
<div class="toolbar">
<button title="Add Condition" id="AddCondition">
<img src="/static/images/new.png" class="toolbar_icon">
</button>

<button title="Add Action" id="AddAction">
<img src="/static/images/new.png" class="toolbar_icon">
</button>

<button title="Delete Rule" id="DeleteRule" >
<img src="/static/images/new.png" class="toolbar_icon">
</button>
</div>
<div id="form_{{unique}}" class="FormBody">
<script id="addRuleTemplate" type="text/x-jquery-tmpl">
  <tbody id="condition_row_${rule_number}">
    <tr><td colspan=3 class="grr_aff4_type_header"><b>Regex Condition</b>
      <a href="#" title="Remove condition"
         onclick="$('#condition_row_${rule_number}').html('');">
         <img src="/static/images/window-close.png" class="toolbar_icon">
      </a>
    </td></tr>
    <tr><td class="proto_key">Path in client</td><td class="proto_value">
      <input name="path_${rule_number}" type=text size=40 /></td></tr>

    <tr><td class="proto_key">Attribute</td><td class="proto_value">
      <select name="attribute_name_${rule_number}" type=text size=1>
        {% for option in attributes %}
          <option>{{option}}</option>
        {% endfor %}
      </select>
    </td> </tr>
    <tr><td class="proto_key">Regex</td><td class="proto_value">
      <input name="attribute_regex_${rule_number}" type=text size=40 /></td>
    </tr>
  </tbody>
</script>

<script id="addActionTemplate" type="text/x-jquery-tmpl">
 <tbody id="action_row_${rule_number}">
   <tr><td colspan=3 class="grr_aff4_type_header"><b>Action</b>
     <a href="#" title="Remove Action"
        onclick="$('#action_row_${rule_number}').html('');">
       <img src="/static/images/window-close.png" class="toolbar_icon">
     </a>
   </td></tr>
   <tr><td class="proto_key">Flow Name</td><td class="proto_value">
     <select name="flow_name_${rule_number}" type=text size=1
       onchange="grr.layout('RenderFlowForm', 'flow_form_${rule_number}',
                            {rule_id: ${rule_id}, flow: this.value,
                             action_id: ${rule_number}});">
       {% for option in flows %}
         <option>{{option}}</option>
       {% endfor %}
     </select>
   </td></tr>
 </tbody>
 <tbody id="flow_form_${rule_number}"></tbody>
</script>

<h1>Add a new automated rule.</h1>
<form id="form">
<input type="hidden" name="rule_id" />
<table id="ForemanFormBody" class="form_table">
<tbody>
<tr><td class="proto_key">Created On</td>
<td class="proto_value">
<input type=text name="created_text" disabled="disabled"/></td>
</tr>

<tr><td class="proto_key">Expires On</td><td class="proto_value">
<input type=text size=20 name="expires_text"/>
</td></tr>

<tr><td class="proto_key">Description</td><td class="proto_value">
<input type=text size=20 name="description"/></td></tr>

</tbody>
</table>
<table id="ForemanFormRuleBody" class="form_table"></table>
<table id="ForemanFormActionBody" class="form_table"></table>

<input id="submit" type="submit" value="Launch"/>
</form>
</div>
<script>
  var defaults = {{ defaults|safe }};

  // Submit button
  $('#submit').button().click(function () {
    return grr.submit('AddForemanRuleAction', 'form', 'form_{{unique}}',
      false, grr.layout);
  });

  $('#AddAction').button().click(function () {
    grr.foreman.add_action({});
  });

  $('#AddCondition').button().click(function () {
    grr.foreman.add_condition({});
  });

  $('#DeleteRule').button().click(function () {
      grr.layout('DeleteRule', 'form_{{unique}}', {rule_id: defaults.rule_id});
  });

  $("[name='expires_text']").datepicker(
    {dateFormat: 'yy-mm-dd', numberOfMonths: 3});

  // Place the first condition
  grr.foreman.regex_rules = 0;
  for (i=0; i<defaults.rule_count; i++) {
    grr.foreman.add_condition(defaults);
  };

  grr.foreman.action_rules = 0;
  for (i=0; i<defaults.action_count; i++) {
    grr.foreman.add_action(defaults);
  };

  grr.update_form('form', defaults);
  grr.subscribe('GeometryChange', function () {
    grr.fixHeight($('#form_{{unique}}'));
  }, 'form_{{unique}}');
</script>
""")

  def Layout(self, request, response):
    """Render the AddForemanRule form."""
    response = renderers.Renderer.Layout(self, request, response)

    defaults = json.dumps(self.BuildDefaults(request))
    flows = [x for x, cls in flow.GRRFlow.classes.items()
             if cls.category]
    flows.sort()

    attributes = [x.name for x in aff4.Attribute.NAMES.values()]
    attributes.sort()

    return self.RenderFromTemplate(self.layout_template, response,
                                   defaults=defaults, flows=flows,
                                   attributes=attributes, unique=self.unique)

  def BuildDefaults(self, request):
    """Prepopulate defaults from old entry."""
    rule_id = request.REQ.get("rule_id")
    result = dict(created=int(time.time() * 1e6),
                  expires=int(time.time() + 60 * 60 * 24) * 1e6,
                  rule_count=1, action_count=1, rule_id=-1)

    if rule_id is not None:
      result["rule_id"] = int(rule_id)
      fd = aff4.FACTORY.Open("aff4:/foreman")
      rules = fd.Get(fd.Schema.RULES)
      if rules is not None:
        rule = rules[result["rule_id"]]

        # Make up the get parameters
        result.update(dict(created=rule.created, expires=rule.expires,
                           description=rule.description))

        for i, regex_rule in enumerate(rule.regex_rules):
          for field_desc, value in regex_rule.ListFields():
            result["%s_%s" % (field_desc.name, i)] = str(value)
            result["rule_count"] = i + 1

        for i, action_rule in enumerate(rule.actions):
          result["flow_name_%s" % i] = action_rule.flow_name

        result["action_count"] = len(rule.actions)

    # Expand the human readable defaults
    result["created_text"] = str(aff4.RDFDatetime(result["created"]))
    result["expires_text"] = str(aff4.RDFDatetime(result["expires"]))

    return result


class RenderFlowForm(AddForemanRule):
  """Render a customized form for a foreman action."""

  layout_template = template.Template("""
{% for desc, field, value, default in fields %}
  <tr><td>{{ desc }}</td>
{% if value %}
 <td><input name="{{field}}_{{rule_number}}" type=text value="{{value}}"/></td>
{% else %}
 <td><input name="{{field}}_{{rule_number}}" type=text value="{{default}}"/>
</td></tr>
{% endif %}
{% endfor %}
""")

  def Layout(self, request, response):
    """Fill in the form with the specific fields for the flow requested."""
    response = renderers.Renderer.Layout(self, request, response)
    rule_id = request.REQ.get("rule_id")
    requested_flow_name = request.REQ.get("flow", "ListDirectory")
    rule_number = int(request.REQ.get("action_id", 0))

    if rule_id is not None:
      rule_id = int(rule_id)

      fd = aff4.FACTORY.Open("aff4:/foreman")
      rules = fd.Get(fd.Schema.RULES)
      if rules is not None:
        try:
          rule = rules[rule_id]
          action = rule.actions[rule_number]
          flow_name = action.flow_name

          # User has not changed the existing flow
          if flow_name == requested_flow_name:
            action_argv = utils.ProtoDict(action.argv).ToDict()
            flow_class = flow.GRRFlow.classes[flow_name]
            args = self.GetArgs(flow_class, request,
                                arg_template="v_%%s_%s" % rule_number)

            fields = []
            for desc, field, _, default in args:
              fields.append((desc, field, action_argv[desc], default))

            args = fields
          # User changed the flow - do not count existing values
          else:
            flow_class = flow.GRRFlow.classes[requested_flow_name]
            args = self.GetArgs(flow_class, request,
                                arg_template="v_%%s_%s" % rule_number)

        except IndexError: pass

    return self.RenderFromTemplate(
        self.layout_template, response, name=flow_name,
        rule_number=rule_number, fields=args)


class AddForemanRuleAction(flow_management.FlowFormAction):
  """Receive the parameters."""

  layout_template = template.Template("""
Created a new automatic rule:
<pre> {{ rule }}</pre>
""")

  error_template = template.Template("""
Error: {{ message }}
""")

  def ParseRegexRules(self, request, foreman_rule):
    """Parse out the request and fill in foreman rules."""
    # These should be more than enough
    for i in range(100):
      try:
        foreman_rule.regex_rules.add(
            path=request.REQ["path_%s" % i],
            attribute_name=request.REQ["attribute_name_%s" % i],
            attribute_regex=request.REQ["attribute_regex_%s" % i])
      except KeyError: pass

  def ParseActionRules(self, request, foreman_rule):
    """Parse and add actions to foreman rule."""
    for i in range(100):
      try:
        flow_name = request.REQ["flow_name_%s" % i]
        flow_class = flow.GRRFlow.classes[flow_name]

        arg_list = self.GetArgs(flow_class, request,
                                arg_template="v_%%s_%s" % i)

        args = self.BuildArgs(arg_list)
        foreman_rule.actions.add(flow_name=flow_name,
                                 argv=utils.ProtoDict(args).ToProto())

      except KeyError: pass

  def AddRuleToForeman(self, foreman_rule):
    """Add the rule to the foreman."""
    fd = aff4.FACTORY.Open("aff4:/foreman")
    rules = fd.Get(fd.Schema.RULES)
    if rules is None: rules = fd.Schema.RULES()
    rules.Append(foreman_rule)
    fd.Set(fd.Schema.RULES, rules)
    fd.Flush()

  def Layout(self, request, response):
    """Process the form action and add a new rule."""
    expire_date = aff4.RDFDatetime()
    expire_date.ParseFromHumanReadable(request.REQ["expires_text"])
    foreman_rule = jobs_pb2.ForemanRule(
        description=request.REQ.get("description", ""),
        created=long(aff4.RDFDatetime()),
        expires=long(expire_date))

    # Check for sanity
    if foreman_rule.expires < foreman_rule.created:
      return self.RenderFromTemplate(self.error_template, response,
                                     message="Rule already expired?")

    self.ParseRegexRules(request, foreman_rule)
    self.ParseActionRules(request, foreman_rule)
    self.AddRuleToForeman(foreman_rule)

    return self.RenderFromTemplate(self.layout_template, response,
                                   rule=foreman_rule)


class DeleteRule(renderers.Renderer):
  """Remove the specified rule from the foreman."""

  layout_template = template.Template("""
<h1> Removed rule {{rule_id}} </h1>
""")

  def Layout(self, request, response):
    """Remove the rule from the foreman."""
    rule_id = int(request.REQ.get("rule_id", -1))
    fd = aff4.FACTORY.Open("aff4:/foreman")
    rules = fd.Get(fd.Schema.RULES)
    new_rules = fd.Schema.RULES()

    if rule_id >= 0 and rules is not None:
      for i, rule in enumerate(rules):
        if i == rule_id: continue

        new_rules.Append(rule)

      # Replace the rules with the new ones
      fd.Set(fd.Schema.RULES, new_rules)
      fd.Flush()

    return self.RenderFromTemplate(
        self.layout_template, response, rule_id=rule_id)


class Empty(renderers.Renderer):
  pass
