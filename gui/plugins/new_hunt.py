#!/usr/bin/env python
"""Implementation of "New Hunt" wizard."""


import collections
import json
import time


from grr.gui import renderers
from grr.gui.plugins import flow_management
from grr.gui.plugins import foreman
from grr.lib import flow
from grr.lib import hunts
from grr.lib import rdfvalue
from grr.lib import type_info
from grr.lib.hunts import output_plugins


class NewHunt(renderers.WizardRenderer):
  """Creates new hunt."""

  wizard_name = "hunt_run"
  title = "New Hunt"
  pages = [
      renderers.WizardPage(
          name="ConfigureFlow",
          description="What to run?",
          renderer="HuntConfigureFlow"),
      renderers.WizardPage(
          name="ConfigureOutput",
          description="Output Processing",
          renderer="HuntConfigureOutputPlugins"),
      renderers.WizardPage(
          name="ConfigureRules",
          description="Where to run?",
          renderer="HuntConfigureRules"),
      renderers.WizardPage(
          name="Review",
          description="Review",
          renderer="HuntInformation",
          next_button_label="Run"),
      renderers.WizardPage(
          name="Done",
          description="Hunt was created.",
          renderer="HuntRunStatus",
          next_button_label="Ok!",
          show_back_button=False)
      ]

  def Layout(self, request, response):
    response = super(NewHunt, self).Layout(request, response)
    return self.CallJavascript(response, "NewHunt.Layout")


class HuntConfigureFlow(renderers.Splitter2WayVertical):
  """Configure hunt's flow."""

  left_renderer = "FlowTree"
  right_renderer = "HuntFlowForm"

  min_left_pane_width = 200

  def Layout(self, request, response):
    response = super(HuntConfigureFlow, self).Layout(request, response)
    return self.CallJavascript(response, "HuntConfigureFlow.Layout")


class HuntFlowForm(flow_management.FlowForm):
  """Flow configuration form that stores the data in wizard's DOM data."""

  # No need to avoid clashes, because the form by itself is not submitted, it's
  # only used by Javascript to form a JSON request.
  prefix = ""

  # There's no sense in displaying "Notify at Completion" argument when
  # configuring hunts
  ignore_flow_args = ["notify_to_user"]

  nothing_selected_template = renderers.Template("""
<div class="padded">Please select a flow.</div>
""")

  layout_template = renderers.Template("""
<div class="HuntFormBody padded" id="FormBody_{{unique|escape}}">
<form id='form_{{unique|escape}}' class="form-horizontal">
<legend>{{this.flow_name|escape}}</legend>

{% if this.flow_name %}

  {{this.flow_args|safe}}

{% else %}
  <p class="text-info">Nothing to configure for the Flow.</p>
{% endif %}
<legend>Hunt Parameters</legend>
{{this.hunt_params_form|safe}}

<legend>Description</legend>
<div id="FlowDescription_{{unique|escape}}"></div>

</div>
""")

  def Layout(self, request, response):
    """Layout the hunt flow form."""
    self.flow_path = request.REQ.get("flow_name", "")
    self.flow_name = self.flow_path.split("/")[-1]

    type_descriptor_renderer = renderers.TypeDescriptorSetRenderer()
    self.hunt_params_form = type_descriptor_renderer.Form(
        hunts.GRRHunt.hunt_typeinfo, request, prefix="")

    if self.flow_name in flow.GRRFlow.classes:
      response = super(HuntFlowForm, self).Layout(request, response)
      return self.CallJavascript(response, "HuntFlowForm.Layout",
                                 flow_name=self.flow_name)
    else:
      return self.RenderFromTemplate(self.nothing_selected_template, response)


# TODO(user): This is very similar to the rules renderer below. We should
# make this more generic and reuse this code below.
class HuntConfigureOutputPlugins(renderers.TemplateRenderer):
  """Configure the hunt's output plugins."""

  layout_template = renderers.Template("""
<script id="HuntsOutputModels_{{unique|escape}}" type="text/x-jquery-tmpl">
  <div class="Rule well well-large">
    {% for plugin_name, plugin_description, plugin_form in this.forms %}
      {% templatetag openvariable %}if output_type == "{{plugin_name}}"
        {% templatetag closevariable %}
        <form name="{{plugin_name|escape}}" class="form-horizontal">
          <div class="control-group">
            <label class="control-label">Output processing</label>
            <div class="controls">
               <select name="output_type">
                 {% for name, description, _ in this.forms %}
                   <option value="{{name|escape}}"
                     {% if name == plugin_name %}selected{% endif %}>
                     {{description|escape}}
                   </option>
                 {% endfor %}
               </select>
            </div>
          </div>
          {{plugin_form|safe}}
          <div class="control-group">
            <div class="controls">
              <input name="remove" class="btn" type="button" value="Remove" />
           </div>
         </div>
        </form>
      {% templatetag openvariable %}/if{% templatetag closevariable %}
    {% endfor %}
  </div>
</script>

<div class="HuntConfigureOutputs padded">
  <div id="HuntsOutputs_{{unique|escape}}" class="RulesList"></div>
  <div class="AddButton">
    <input type="button" class="btn" id="AddHuntOutput_{{unique|escape}}"
      value="Add another output plugin" />
  </div>
</div>

""")

  def Layout(self, request, response):
    """Layout hunt output plugins."""
    type_descriptor_renderer = renderers.TypeDescriptorSetRenderer()

    self.forms = []
    self.output_options = []

    for name, plugin in output_plugins.HuntOutputPlugin.classes.items():
      if plugin.description:
        self.forms.append((
            name, plugin.description, type_descriptor_renderer.Form(
                plugin.output_typeinfo, request, prefix="")))

    response = super(HuntConfigureOutputPlugins, self).Layout(request, response)
    return self.CallJavascript(response, "HuntConfigureOutput.Layout")


# TODO(user): we should have RDFProtoEditableRenderer or the likes to have
# a generic way of displaying forms for editing protobufs. Maybe it should be
# based on RDFProtoRenderer code.
class HuntConfigureRules(renderers.TemplateRenderer):
  """Configure hunt's rules."""

  match_system_template = renderers.Template("""
This rule will match all <strong>{{system}}</strong> systems.
""")

  # We generate jQuery template for different kind of rules that we have (i.e.
  # ForemanAttributeInteger, ForemanAttributeRegex). For every
  # cloned rule form, we register "change" event listener, which updates
  # wizard's configuration (by convention stored in wizard's DOM by using
  # jQuery.data()).
  layout_template = renderers.Template("""
<script id="HuntsRulesModels_{{unique|escape}}" type="text/x-jquery-tmpl">
  <div class="Rule well well-large">
    {% for form_name, form in this.forms.items %}
      {% templatetag openvariable %}if rule_type == "{{form_name}}"
        {% templatetag closevariable %}
        <form name="{{form_name|escape}}" class="form-horizontal">
          <div class="control-group">
            <label class="control-label">Rule Type</label>
            <div class="controls">
               <select name="rule_type">
                 {% for fn in this.forms.iterkeys %}
                   <option value="{{fn|escape}}"
                     {% if fn == form_name %}selected{% endif %}>
                     {{fn|escape}}
                   </option>
                 {% endfor %}
               </select>
            </div>
          </div>
          {{form|safe}}
          <div class="control-group">
            <div class="controls">
              <input name="remove" class="btn" type="button" value="Remove" />
           </div>
         </div>
        </form>
      {% templatetag openvariable %}/if{% templatetag closevariable %}
    {% endfor %}
  </div>
</script>

<div class="HuntConfigureRules padded">
  <div id="HuntsRules_{{unique|escape}}" class="RulesList"></div>
  <div class="AddButton">
    <input type="button" class="btn" id="AddHuntRule_{{unique|escape}}"
      value="Add Rule" />
  </div>
</div>

""")

  def Layout(self, request, response):
    """Layout hunt rules."""
    type_descriptor_renderer = renderers.TypeDescriptorSetRenderer()

    self.forms = collections.OrderedDict()
    self.forms["Windows systems"] = self.FormatFromTemplate(
        self.match_system_template, system="Windows")
    self.forms["Linux systems"] = self.FormatFromTemplate(
        self.match_system_template, system="Linux")
    self.forms["Mac OS X systems"] = self.FormatFromTemplate(
        self.match_system_template, system="Mac OS X")
    self.forms["Regular expression match"] = type_descriptor_renderer.Form(
        type_info.TypeDescriptorSet(type_info.ForemanAttributeRegexType()),
        request, prefix="")
    self.forms["Integer comparison"] = type_descriptor_renderer.Form(
        type_info.TypeDescriptorSet(type_info.ForemanAttributeIntegerType()),
        request, prefix="")

    response = super(HuntConfigureRules, self).Layout(request, response)
    return self.CallJavascript(response, "HuntConfigureRules.Layout")


class HuntRequestParsingMixin(object):
  """Mixin with hunt's JSON configuration parsing methods."""

  PREDEFINED_RULES = {"Windows systems": hunts.GRRHunt.MATCH_WINDOWS,
                      "Linux systems": hunts.GRRHunt.MATCH_LINUX,
                      "Mac OS X systems": hunts.GRRHunt.MATCH_DARWIN}

  def ParseFlowConfig(self, flow_class, flow_args_json):
    """Parse flow config JSON."""

    type_descriptor_renderer = renderers.TypeDescriptorSetRenderer()
    # We ignore certain args in HuntFlowForm therefore we shouldn't parse
    # it here.
    tinfo = flow_class.flow_typeinfo
    for arg in HuntFlowForm.ignore_flow_args:
      try:
        tinfo = tinfo.Remove(arg)
      except KeyError:
        pass  # this flow_arg was not part of the request

    flow_config = rdfvalue.Dict(
        initializer=dict(type_descriptor_renderer.ParseArgs(
            tinfo, flow_args_json, prefix="")))
    return flow_config

  def ParseHuntRules(self, hunt_rules_json):
    """Parse rules config JSON."""

    type_descriptor_renderer = renderers.TypeDescriptorSetRenderer()
    result = []
    for rule_json in hunt_rules_json:
      rule_type = rule_json["rule_type"]

      if rule_type in self.PREDEFINED_RULES:
        result.append(self.PREDEFINED_RULES[rule_type])
        continue

      if rule_type == "Regular expression match":
        tinfo = type_info.TypeDescriptorSet(
            type_info.ForemanAttributeRegexType())
      elif rule_type == "Integer comparison":
        tinfo = type_info.TypeDescriptorSet(
            type_info.ForemanAttributeIntegerType())
      else:
        raise RuntimeError("Unknown rule type: " + rule_type)

      parse_result = dict(type_descriptor_renderer.ParseArgs(
          tinfo, rule_json, prefix=""))

      rdf_rule = parse_result["foreman_attributes"]
      result.append(rdf_rule)

    return result

  def ParseOutputConfig(self, output_config_json):
    """Parse the output configuration."""

    output_parameters = []
    for config_set in output_config_json:
      try:
        plugin_name = config_set["output_type"]
      except KeyError:
        continue

      output_cls = output_plugins.HuntOutputPlugin.classes.get(plugin_name)
      if output_cls is None:
        continue

      parse_result = dict(renderers.TypeDescriptorSetRenderer().ParseArgs(
          output_cls.output_typeinfo, config_set, prefix=""))
      output_parameters.append((plugin_name, parse_result))
    return output_parameters

  def ParseExpiryTime(self, timestring):
    """Parses the expiration time."""
    multiplicator = 1

    if not timestring:
      return None
    orig_string = timestring

    if timestring[-1].isdigit():
      pass
    else:
      if timestring[-1] == "s":
        pass
      elif timestring[-1] == "m":
        multiplicator = 60
      elif timestring[-1] == "h":
        multiplicator = 60*60
      elif timestring[-1] == "d":
        multiplicator = 60*60*24
      timestring = timestring[:-1]
    try:
      return int(timestring) * multiplicator
    except ValueError:
      raise RuntimeError("Could not parse expiration time '%s'." % orig_string)

  def GetHuntArgsFromRequest(self, request):
    """Parse JSON'ed hunt configuration from request into hunt object."""
    hunt_config_json = request.REQ.get("hunt_run")
    hunt_config = json.loads(hunt_config_json)

    flow_name = hunt_config["hunt_flow_name"]
    flow_config_json = hunt_config.get("hunt_flow_config", {})
    rules_config_json = hunt_config["hunt_rules_config"]
    output_config_json = hunt_config["hunt_output_config"]

    type_descriptor_renderer = renderers.TypeDescriptorSetRenderer()
    hunt_args = dict(type_descriptor_renderer.ParseArgs(
        hunts.GRRHunt.hunt_typeinfo, flow_config_json, prefix=""))

    flow_class = flow.GRRFlow.classes[flow_name]
    flow_config = self.ParseFlowConfig(flow_class, flow_config_json or {})
    rules_config = self.ParseHuntRules(rules_config_json)
    output_config = self.ParseOutputConfig(output_config_json)

    return {"hunt_name": "GenericHunt",
            "hunt_args": hunt_args,
            "flow_name": flow_name,
            "flow_args": flow_config,
            "rules": rules_config,
            "output": output_config}


class HuntRuleInformation(foreman.ReadOnlyForemanRuleTable,
                          HuntRequestParsingMixin):
  """Renders hunt's rules table, getting rules configuration from request."""

  post_parameters = ["hunt_run"]

  def RenderAjax(self, request, response):
    """Renders information about the newly created rules."""
    args = self.GetHuntArgsFromRequest(request)
    for rule in hunts.GRRHunt.CreateForemanRule(args["rules"],
                                                "aff4:/hunts/W:TBD"):
      expiry_time = rdfvalue.RDFDatetime(
          (time.time() + args["hunt_args"]["expiry_time"].seconds) * 1e6)
      self.AddRow(dict(Created=rdfvalue.RDFDatetime().Now(),
                       Expires=expiry_time,
                       Description=rule.description,
                       Rules=rule,
                       Actions=rule))

    return renderers.TableRenderer.RenderAjax(self, request, response)


class HuntInformation(renderers.TemplateRenderer, HuntRequestParsingMixin):
  """Displays information about a hunt: flow settings and rules."""

  failure_reason = None
  failure_template = renderers.Template("""
<div class="Failure padded">
<p class="text-error">Failure due: <span class="Reason">
  {{this.failure_reason|escape}}</span></p>
</div>
""")

  layout_template = renderers.Template("""
<div class="HuntInformation padded" id="HuntInformation_{{unique|escape}}">
  {{this.hunt_details|safe}}
</div>
""")

  hunt_details_template = renderers.Template("""
  <div class="Flow">
    <h3>{{this.hunt_name|escape}}</h3>

    {% if this.args.items %}
      <h4>Settings</h4>
      <dl class="dl-horizontal">
        {% for key,value in this.args.items %}
        <dt>{{key|escape}}</dt>
        <dd>{{value|escape}}</dd>
        {% endfor %}
      </dl>
    {% else %}
       No arguments.
    {% endif %}
  </div>

  <!-- Classes inherited from HuntInformation may fill this div with
  something. -->
  <div class="Misc"></div>

  <h3>Output Processing</h3>
  <div id="HuntOutputInformation_{{unique|escape}}" class="Rules">
{% for plugin, args in this.output_information %}
- {{plugin|escape}} {{args|safe}} <br />
{% endfor %}
</div>

  <h3>Rules</h3>
  <div id="HuntRuleInformation_{{unique|escape}}" class="Rules"></div>
""")

  @property
  def hunt_details(self):
    return self.FormatFromTemplate(self.hunt_details_template, this=self,
                                   unique=self.unique)

  def Fail(self, reason, request, response):
    """Render failure_template instead of layout_template."""

    self.failure_reason = reason
    return renderers.TemplateRenderer.Layout(
        self, request, response, apply_template=self.failure_template)

  def Layout(self, request, response):
    """Layout the hunt information."""
    try:
      self.hunt_args = self.GetHuntArgsFromRequest(request)
      self.hunt_name = self.hunt_args["hunt_name"]
      self.args = self.hunt_args["hunt_args"]
      self.args.update(self.hunt_args["flow_args"].ToDict())
      self.output_information = []
      for plugin_name, args in self.hunt_args["output"]:
        try:
          cls = output_plugins.HuntOutputPlugin.classes[plugin_name]
        except KeyError:
          self.output_information.append(
              ("Unknown plugin: %s" % plugin_name, ""))
          continue

        if args:
          args_html = renderers.FindRendererForObject(args).RawHTML()
        else:
          args_html = ""
        self.output_information.append((cls.description, args_html))

    except RuntimeError, e:
      return self.Fail(e, request, response)

    response = renderers.TemplateRenderer.Layout(self, request, response)
    return self.CallJavascript(response, "HuntInformation.Layout")


class HuntRunStatus(renderers.TemplateRenderer, HuntRequestParsingMixin):
  """Launches the hunt and displays status summary."""

  layout_template = renderers.Template("""
<div class="HuntLaunchSummary padded">
  <p class="text-success">Hunt was created!</p>
</div>
""")

  def Layout(self, request, response):
    """Attempt to run a CreateAndRunGenericHuntFlow."""
    hunt_args = self.GetHuntArgsFromRequest(request)

    try:
      # This should fail with UnauthorizedAccess error, because the hunt that
      # was just created doesn't have required number of approvals.
      flow.GRRFlow.StartFlow(
          None, "CreateAndRunGenericHuntFlow",
          token=request.token,
          expiry_time=hunt_args["hunt_args"]["expiry_time"],
          client_limit=hunt_args["hunt_args"]["client_limit"],
          hunt_flow_name=hunt_args["flow_name"],
          hunt_flow_args=hunt_args["flow_args"],
          hunt_rules=hunt_args["rules"],
          output_plugins=hunt_args["output"])
    except RuntimeError, e:
      return self.Fail(e, request, response)

    return super(HuntRunStatus, self).Layout(request, response)
