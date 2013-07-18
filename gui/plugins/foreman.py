#!/usr/bin/env python
# -*- mode: python; encoding: utf-8 -*-
#
# Copyright 2010 Google Inc. All Rights Reserved.

"""This is the interface for managing the foreman."""


import json
import time

from grr.gui import renderers
from grr.gui.plugins import flow_management
from grr.lib import aff4
from grr.lib import flow
from grr.lib import rdfvalue


class ManageForeman(renderers.UserLabelCheckMixin, renderers.Splitter2Way):
  """Manages class based flow creation."""
  description = "Automated flows"
  behaviours = frozenset(["General"])
  AUTHORIZED_LABELS = ["admin"]
  top_renderer = "ReadOnlyForemanRuleTable"
  bottom_renderer = "EmptyRenderer"


class RegexRuleArray(renderers.RDFValueArrayRenderer):
  """Nicely render all the rules."""
  proxy_field = "regex_rules"


class ActionRuleArray(renderers.RDFValueArrayRenderer):
  """Nicely render all the actions for a rule."""
  proxy_field = "actions"

  translator = dict(argv=renderers.RDFProtoRenderer.ProtoDict)


class ReadOnlyForemanRuleTable(renderers.TableRenderer):
  """Show all the foreman rules."""

  def __init__(self, **kwargs):
    super(ReadOnlyForemanRuleTable, self).__init__(**kwargs)
    self.AddColumn(renderers.RDFValueColumn("Created"))
    self.AddColumn(renderers.RDFValueColumn("Expires"))
    self.AddColumn(renderers.RDFValueColumn("Description"))
    self.AddColumn(renderers.RDFValueColumn(
        "Rules", renderer=RegexRuleArray, width="100%"))

  def RenderAjax(self, request, response):
    """Renders the table."""
    fd = aff4.FACTORY.Open("aff4:/foreman", token=request.token)
    rules = fd.Get(fd.Schema.RULES, [])
    for rule in rules:
      self.AddRow(Created=rule.created,
                  Expires=rule.expires,
                  Description=rule.description,
                  Rules=rule,
                  Actions=rule)

    # Call our baseclass to actually do the rendering
    return super(ReadOnlyForemanRuleTable, self).RenderAjax(request, response)


class ForemanRuleTable(ReadOnlyForemanRuleTable, renderers.UserLabelCheckMixin):
  """Show all existing rules and allow for editing."""

  selection_publish_queue = "rule_select"

  AUTHORIZED_LABELS = ["admin"]

  layout_template = renderers.TableRenderer.layout_template + """
<script>
  //Receive the selection event and emit the rule creation time.
  grr.subscribe("select_table_{{ id|escapejs }}", function(node) {
    if (node) {
      var row_id = node.attr("row_id");
      grr.layout("AddForemanRule", "main_bottomPane", {rule_id: row_id});
      grr.publish("{{ this.selection_publish_queue|escapejs }}", row_id);
    };
  }, '{{ unique|escapejs }}');

</script>
"""

  def Layout(self, request, response):
    # First render the toolbar.
    ForemanToolbar().Layout(request, response)
    return super(ForemanRuleTable, self).Layout(request, response)


class ForemanToolbar(renderers.TemplateRenderer):
  """Renders the toolbar."""

  layout_template = renderers.Template("""
<button id="add_rule" title="Add a new rule." class="grr-button">
  Add Rule
</button>
<script>
  $("#add_rule").button().click(function () {
     grr.layout("AddForemanRule", "main_bottomPane");
  });
</script>
""")


class AddForemanRule(flow_management.FlowInformation):
  """Present a form to add a new rule."""

  layout_template = renderers.Template("".join((
      # This is the toolbar for manipulating the rule
      """
<div class="toolbar">
<button title="Add Condition" id="AddCondition" class="grr-button">
Add Condition
</button>

<button title="Add Action" id="AddAction" class="grr-button">
Add Action
</button>

<button title="Delete Rule" id="DeleteRule" class="grr-button">
Delete Rule
</button>
</div>
""",

      # Scripts to add new rules based on jquery templates
      """<div id="form_{{unique|escapejs}}" class="FormBody">
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
        {% for option in this.attributes %}
          <option>{{option|escape}}</option>
        {% endfor %}
      </select>
    </td> </tr>
    <tr><td class="proto_key">Regex</td><td class="proto_value">
      <input name="attribute_regex_${rule_number}" type=text size=40 /></td>
    </tr>
  </tbody>
</script>""",

      # Scripts to add a new action based on jquery templates
      """<script id="addActionTemplate" type="text/x-jquery-tmpl">
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
         <option>Select a Flow</option>
       {% for option in this.flows %}
         <option>{{option|escape}}</option>
       {% endfor %}
     </select>
   </td></tr>
 </tbody>
 <tbody id="flow_form_${rule_number}"></tbody>
</script>""",

      # Rendering the actual form
      """<h1>Add a new automated rule.</h1>
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
</div>""",

      # Initialize the form - adds actions to toolbar items
      """<script>
  var defaults = {{ this.defaults|safe }};

  // Submit button
  $('#submit').button().click(function () {
    return grr.submit('AddForemanRuleAction', 'form',
      'form_{{unique|escapejs}}', false, grr.layout);
  });

  $('#AddAction').button().click(function () {
    grr.foreman.add_action({rule_id: defaults.rule_id});
  });

  $('#AddCondition').button().click(function () {
    grr.foreman.add_condition({rule_id: defaults.rule_id});
  });

  $('#DeleteRule').button().click(function () {
      grr.layout('DeleteRule', 'form_{{unique|escapejs}}',
      {rule_id: defaults.rule_id});
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
</script>
""")))

  def Layout(self, request, response):
    """Render the AddForemanRule form."""
    self.defaults = json.dumps(self.BuildDefaults(request))
    self.flows = [x for x, cls in flow.GRRFlow.classes.items()
                  if cls.category]
    self.flows.sort()

    self.attributes = [x.name for x in aff4.Attribute.NAMES.values()]
    self.attributes.sort()

    return renderers.TemplateRenderer.Layout(self, request, response)

  def BuildDefaults(self, request):
    """Prepopulate defaults from old entry."""
    rule_id = request.REQ.get("rule_id")
    result = dict(created=int(time.time() * 1e6),
                  expires=int(time.time() + 60 * 60 * 24) * 1e6,
                  rule_count=1, action_count=1, rule_id=-1)

    if rule_id is not None:
      result["rule_id"] = int(rule_id)
      fd = aff4.FACTORY.Open("aff4:/foreman", token=request.token)
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
    result["created_text"] = str(rdfvalue.RDFDatetime(result["created"]))
    result["expires_text"] = str(rdfvalue.RDFDatetime(result["expires"]))

    return result


class RenderFlowForm(AddForemanRule, flow_management.FlowForm):
  """Render a customized form for a foreman action."""

  layout_template = renderers.Template("""
{% for row in this.form_elements %}
  <tr> {{ row|escape }} </tr>
{% endfor %}
<script>
  // Fixup checkboxes so they return values even if unchecked.
  $(".FormBody").find("input[type=checkbox]").change(function() {
    $(this).attr("value", $(this).attr("checked") ? "True" : "False");
  });
</script>
""")

  def Layout(self, request, response):
    """Fill in the form with the specific fields for the flow requested."""
    response = renderers.Renderer.Layout(self, request, response)
    rule_id = request.REQ.get("rule_id")
    requested_flow_name = request.REQ.get("flow", "ListDirectory")
    rule_number = int(request.REQ.get("action_id", 0))

    args = []
    if rule_id is not None and int(rule_id) != -1:
      rule_id = int(rule_id)

      fd = aff4.FACTORY.Open("aff4:/foreman", token=request.token)
      rules = fd.Get(fd.Schema.RULES)
      if rules is not None:
        try:
          rule = rules[rule_id]
          action = rule.actions[rule_number]
          flow_name = action.flow_name

          # User has not changed the existing flow
          if flow_name == requested_flow_name:
            action_argv = action.argv.ToDict()
            flow_class = flow.GRRFlow.classes[flow_name]
            args = self.GetArgs(flow_class, request,
                                arg_template="v_%%s_%s" % rule_number)

            fields = []
            for desc, field, _, default in args:
              fields.append((desc, field, action_argv[desc], default))

            args = fields

        except IndexError:
          pass

    # User changed the flow - do not count existing values
    if not args:
      flow_class = flow.GRRFlow.classes[requested_flow_name]
      args = self.GetArgs(flow_class, request,
                          arg_template="v_%%s_%s" % rule_number)

    self.form_elements = self.RenderFormElements(args)

    return renderers.TemplateRenderer.Layout(self, request, response)


class AddForemanRuleAction(flow_management.FlowFormAction,
                           renderers.UserLabelCheckMixin):
  """Receive the parameters."""
  AUTHORIZED_LABELS = ["admin"]

  layout_template = renderers.Template("""
Created a new automatic rule:
<pre> {{ this.foreman_rule|escape }}</pre>
<script>
 grr.publish("grr_messages", "Created Foreman Rule");
</script>
""")

  error_template = renderers.Template("""
Error: {{ message|escape }}
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
      except KeyError:
        pass

  def ParseActionRules(self, request, foreman_rule):
    """Parse and add actions to foreman rule."""
    for i in range(100):
      flow_name = request.REQ.get("flow_name_%s" % i)
      if not flow_name: continue

      flow_class = flow.GRRFlow.classes[flow_name]

      arg_list = self.GetArgs(flow_class, request,
                              arg_template="v_%%s_%s" % i)
      args = dict([(k, v) for (k, _, _, v, _) in arg_list])
      foreman_rule.actions.add(flow_name=flow_name,
                               argv=rdfvalue.ProtoDict(args))

  def AddRuleToForeman(self, foreman_rule, token):
    """Add the rule to the foreman."""
    fd = aff4.FACTORY.Create("aff4:/foreman", "GRRForeman",
                             mode="rw", token=token)
    rules = fd.Get(fd.Schema.RULES)
    if rules is None: rules = fd.Schema.RULES()
    rules.Append(foreman_rule)
    fd.Set(fd.Schema.RULES, rules)
    fd.Close()

  @renderers.ErrorHandler()
  def Layout(self, request, response):
    """Process the form action and add a new rule."""
    expire_date = rdfvalue.RDFDatetime.ParseFromHumanReadable(
        request.REQ["expires_text"])
    self.foreman_rule = rdfvalue.ForemanRule(
        description=request.REQ.get("description", ""),
        created=rdfvalue.RDFDatetime().Now(),
        expires=expire_date)

    # Check for sanity
    if self.foreman_rule.expires < self.foreman_rule.created:
      return self.RenderFromTemplate(self.error_template, response,
                                     message="Rule already expired?")

    self.ParseRegexRules(request, self.foreman_rule)
    self.ParseActionRules(request, self.foreman_rule)
    self.AddRuleToForeman(self.foreman_rule, request.token)

    return renderers.TemplateRenderer.Layout(self, request, response)


class DeleteRule(renderers.TemplateRenderer, renderers.UserLabelCheckMixin):
  """Remove the specified rule from the foreman."""
  AUTHORIZED_LABELS = ["admin"]

  layout_template = renderers.Template("""
<h1> Removed rule {{this.rule_id|escape}} </h1>
""")

  def Layout(self, request, response):
    """Remove the rule from the foreman."""
    self.rule_id = int(request.REQ.get("rule_id", -1))
    fd = aff4.FACTORY.Open("aff4:/foreman", mode="rw", token=request.token)
    rules = fd.Get(fd.Schema.RULES)
    new_rules = fd.Schema.RULES()

    if self.rule_id >= 0 and rules is not None:
      for i, rule in enumerate(rules):
        if i == self.rule_id: continue

        new_rules.Append(rule)

      # Replace the rules with the new ones
      fd.Set(fd.Schema.RULES, new_rules)
      fd.Close()

    return renderers.TemplateRenderer.Layout(self, request, response)
