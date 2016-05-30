#!/usr/bin/env python
"""Implementation of "New Hunt" wizard."""


import os

import logging

from grr.gui import renderers
from grr.gui.plugins import flow_management
from grr.gui.plugins import forms
from grr.gui.plugins import wizards
from grr.lib import aff4
from grr.lib import config_lib
from grr.lib import flow
from grr.lib import flow_runner
from grr.lib import output_plugin
from grr.lib import type_info
from grr.lib.hunts import implementation
from grr.lib.hunts import standard
from grr.lib.rdfvalues import aff4_rdfvalues
from grr.server import foreman as rdf_foreman


class HuntArgsParser(object):
  """A utility class for parsing the hunt parameters."""

  flow_runner_args = None
  flow_args = None
  hunt_args = None
  hunt_runner_args = None

  def __init__(self, request):
    self.request = request

  def ParseRules(self, hunt_runner_args):
    """Parse the rules into the hunt_runner_args."""
    # Clear all the rules from the hunt runner.
    hunt_runner_args.regex_rules = hunt_runner_args.integer_rules = None

    for option in ConfigureHuntRules().ParseArgs(self.request):
      # Options can be either regex or integer rules.
      if option.__class__ is rdf_foreman.ForemanAttributeRegex:
        hunt_runner_args.regex_rules.Append(option)
      elif option.__class__ is rdf_foreman.ForemanAttributeInteger:
        hunt_runner_args.integer_rules.Append(option)

  def ParseFlowArgs(self):
    """Parse the flow and flow_runner args."""
    if self.flow_runner_args is not None:
      return self.flow_runner_args, self.flow_args

    flow_path = self.request.REQ.get("flow_path", "")
    flow_name = os.path.basename(flow_path)
    if not flow_name:
      raise ValueError("No flow specified. Please select a flow.")

    flow_cls = flow.GRRFlow.GetPlugin(flow_name)
    self.flow_args = forms.SemanticProtoFormRenderer(
        flow_cls.args_type(), prefix="args").ParseArgs(self.request)

    self.flow_runner_args = forms.SemanticProtoFormRenderer(
        flow_runner.FlowRunnerArgs(),
        prefix="runner").ParseArgs(self.request)

    self.flow_runner_args.flow_name = flow_name

    return self.flow_runner_args, self.flow_args

  def ParseOutputPlugins(self):
    return HuntConfigureOutputPlugins().ParseArgs(self.request)

  def ParseHuntRunnerArgs(self):
    """Parse the hunt runner arguments, rules and output plugins."""
    if self.hunt_runner_args is not None:
      return self.hunt_runner_args

    self.hunt_runner_args = forms.SemanticProtoFormRenderer(
        implementation.HuntRunnerArgs(),
        prefix="hunt_runner").ParseArgs(self.request)

    self.hunt_runner_args.hunt_name = "GenericHunt"

    # Parse out the rules.
    self.ParseRules(self.hunt_runner_args)

    return self.hunt_runner_args

  def ParseHuntArgs(self):
    """Build the hunt args from the self.request."""
    if self.hunt_args is not None:
      return self.hunt_args

    flow_runner_args, flow_args = self.ParseFlowArgs()

    self.hunt_args = standard.GenericHuntArgs(
        flow_runner_args=flow_runner_args,
        flow_args=flow_args,
        output_plugins=self.ParseOutputPlugins())

    return self.hunt_args


class HuntConfigureFlow(renderers.Splitter2WayVertical):
  """Configure the generic hunt's flow."""

  description = "What to run?"
  left_renderer = "FlowTree"
  right_renderer = "HuntFlowForm"

  min_left_pane_width = 200

  def Layout(self, request, response):
    response = super(HuntConfigureFlow, self).Layout(request, response)
    return self.CallJavascript(response, "Layout")

  def Validate(self, request, _):
    """Check the flow args are valid."""
    parser = HuntArgsParser(request)

    flow_runner_args, flow_args = parser.ParseFlowArgs()
    flow_runner_args.Validate()
    flow_args.Validate()

    hunt_runner_args = parser.ParseHuntRunnerArgs()
    hunt_runner_args.Validate()


class HuntFlowForm(flow_management.SemanticProtoFlowForm):
  """Flow configuration form that stores the data in wizard's DOM data."""

  nothing_selected_template = renderers.Template("""
<div class="padded">Please select a flow.</div>
""")

  layout_template = renderers.Template("""
<div class="HuntFormBody padded" id="FormBody_{{unique|escape}}">
<form id='form_{{unique|escape}}' class="form-horizontal">
<legend>{{this.flow_name|escape}}</legend>

{% if this.flow_name %}

  {{this.form|safe}}
  <hr/>
  {{this.runner_form|safe}}

{% else %}
  <p class="text-info">Nothing to configure for the Flow.</p>
{% endif %}
<legend>Hunt Parameters
  <a href="/help/user_manual.html#hunt-parameters" target="_blank">
  <i class="glyphicon glyphicon-question-sign"></i></a>
</legend>
{{this.hunt_params_form|safe}}

<legend>Description</legend>

{{this.flow_description|safe}}
</div>
""")

  # These rules are filled in separately.
  suppressions = ["hunt_name", "regex_rules", "integer_rules"]

  def Layout(self, request, response):
    """Layout the hunt flow form."""
    self.flow_path = request.REQ.get("flow_path", "")
    self.flow_name = os.path.basename(self.flow_path)

    hunt_runner_form = forms.SemanticProtoFormRenderer(
        implementation.HuntRunnerArgs(),
        id=self.id,
        supressions=self.suppressions,
        prefix="hunt_runner")

    self.hunt_params_form = hunt_runner_form.RawHTML(request)

    self.flow_description = flow_management.FlowInformation(
        id=self.id).RawHTML(request)

    if self.flow_name in flow.GRRFlow.classes:
      return super(HuntFlowForm, self).Layout(request, response)
    else:
      return self.RenderFromTemplate(self.nothing_selected_template, response)


class OutputPluginsForm(forms.OptionFormRenderer):
  """Render and parse the form for output plugin selection."""
  friendly_name = "Output Plugin"
  help = "Select and output plugin for processing hunt results."
  option_name = "output"

  @property
  def options(self):
    """Only include output plugins with descriptions."""
    for name in sorted(output_plugin.OutputPlugin.classes.keys()):
      cls = output_plugin.OutputPlugin.classes[name]
      if cls.description:
        yield name, cls.description

  def ParseOption(self, option, request):
    # Depending on the plugin we parse a different protobuf.
    plugin = output_plugin.OutputPlugin.classes.get(option)

    if plugin and plugin.description:
      result = output_plugin.OutputPluginDescriptor(plugin_name=option)
      result.plugin_args = forms.SemanticProtoFormRenderer(
          plugin.args_type(), id=self.id,
          prefix=self.prefix).ParseArgs(request)
      result.plugin_args.Validate()

      return result

  def RenderOption(self, option, request, response):
    # Depending on the plugin we render a different protobuf.
    plugin = output_plugin.OutputPlugin.classes.get(option)

    if plugin and plugin.description:
      return forms.SemanticProtoFormRenderer(
          plugin.args_type(), id=self.id,
          prefix=self.prefix).Layout(request, response)


class HuntConfigureOutputPlugins(forms.MultiFormRenderer):
  """Allow multiple output plugins to be specified."""

  child_renderer = OutputPluginsForm
  option_name = "output"
  button_text = "Add Output Plugin"
  description = "Define Output Processing"
  add_one_default = False

  def Layout(self, request, response):
    response = super(HuntConfigureOutputPlugins, self).Layout(request, response)
    return self.CallJavascript(
        response,
        "HuntConfigureOutputPlugins.Layout",
        default_output_plugin=config_lib.CONFIG[
            "AdminUI.new_hunt_wizard.default_output_plugin"])

  def Validate(self, request, _):
    # Check each plugin for validity.
    parser = HuntArgsParser(request)
    for plugin in parser.ParseOutputPlugins():
      plugin.Validate()


class ClientLabelNameFormRenderer(forms.TypeDescriptorFormRenderer):
  """A renderer for AFF4 object label name."""

  layout_template = """<div class="form-group">
""" + forms.TypeDescriptorFormRenderer.default_description_view + """
<div class="controls">

<select id="{{this.prefix}}" class="unset"
  onchange="grr.forms.inputOnChange(this)"
  >
{% for label in this.labels %}
   <option {% if forloop.first %}selected{% endif %}
     value="{{label|escape}}">
     {{label|escape}}
   </option>
{% endfor %}
</select>
</div>
</div>
"""

  def Layout(self, request, response):
    labels_index = aff4.FACTORY.Create(standard.LabelSet.CLIENT_LABELS_URN,
                                       "LabelSet",
                                       mode="r",
                                       token=request.token)
    self.labels = sorted(list(set(
        [label.name for label in labels_index.ListUsedLabels()])))

    response = super(ClientLabelNameFormRenderer, self).Layout(request,
                                                               response)
    return self.CallJavascript(response,
                               "AFF4ObjectLabelNameFormRenderer.Layout",
                               prefix=self.prefix)


class RuleOptionRenderer(forms.OptionFormRenderer):
  """Make a rule form based on rule type."""
  options = (("Windows", "Windows"),
             ("Linux", "Linux"),
             ("OSX", "OSX"),
             ("Label", "Clients With Label"),
             ("Regex", "Regular Expressions"),
             ("Integer", "Integer Rule"))  # pyformat: disable

  option_name = "rule"
  help = "Rule Type"
  friendly_name = "Rule Type"

  match_system_template = renderers.Template("""
This rule will match all <strong>{{system}}</strong> systems.
""")

  form_template = renderers.Template("""{{form|safe}}""")

  def RenderOption(self, option, request, response):
    if option == "Windows":
      return self.RenderFromTemplate(self.match_system_template,
                                     response,
                                     system="Windows")

    elif option == "Linux":
      return self.RenderFromTemplate(self.match_system_template,
                                     response,
                                     system="Linux")

    elif option == "OSX":
      return self.RenderFromTemplate(self.match_system_template,
                                     response,
                                     system="OSX")

    elif option == "Label":
      return self.RenderFromTemplate(
          self.form_template,
          response,
          form=ClientLabelNameFormRenderer(
              descriptor=type_info.TypeInfoObject(friendly_name="Label"),
              default="",
              prefix=self.prefix).RawHTML(request))

    elif option == "Regex":
      return self.RenderFromTemplate(self.form_template,
                                     response,
                                     form=forms.SemanticProtoFormRenderer(
                                         rdf_foreman.ForemanAttributeRegex(),
                                         prefix=self.prefix).RawHTML(request))

    elif option == "Integer":
      return self.RenderFromTemplate(self.form_template,
                                     response,
                                     form=forms.SemanticProtoFormRenderer(
                                         rdf_foreman.ForemanAttributeInteger(),
                                         prefix=self.prefix).RawHTML(request))

  def ParseOption(self, option, request):
    """Parse the form that is selected by option."""
    if option == "Windows":
      return implementation.GRRHunt.MATCH_WINDOWS

    elif option == "Linux":
      return implementation.GRRHunt.MATCH_LINUX

    elif option == "OSX":
      return implementation.GRRHunt.MATCH_DARWIN

    elif option == "Label":
      label_name = ClientLabelNameFormRenderer(
          descriptor=type_info.TypeInfoObject(),
          default="",
          prefix=self.prefix).ParseArgs(request)
      regex = aff4_rdfvalues.AFF4ObjectLabelsList.RegexForStringifiedValueMatch(
          label_name)

      return rdf_foreman.ForemanAttributeRegex(attribute_name="Labels",
                                               attribute_regex=regex)

    elif option == "Regex":
      return forms.SemanticProtoFormRenderer(
          rdf_foreman.ForemanAttributeRegex(),
          prefix=self.prefix).ParseArgs(request)

    elif option == "Integer":
      return forms.SemanticProtoFormRenderer(
          rdf_foreman.ForemanAttributeInteger(),
          prefix=self.prefix).ParseArgs(request)


class ConfigureHuntRules(forms.MultiFormRenderer):
  """Allow configuration of only the rules."""

  option_name = "rule"
  button_text = "Add Rule"
  child_renderer = RuleOptionRenderer
  description = "Where to run?"

  def Validate(self, request, _):
    parser = HuntArgsParser(request)
    hunt_runner_args = parser.ParseHuntRunnerArgs()
    hunt_runner_args.regex_rules.Validate()
    hunt_runner_args.integer_rules.Validate()


class HuntInformation(renderers.TemplateRenderer):
  """Displays information about a hunt: flow settings and rules."""

  description = "Review"

  layout_template = renderers.Template("""
<div class="HuntInformation padded" id="{{unique|escape}}">
 Loading...
</div>
""")

  ajax_template = renderers.Template("""
  <h3>Hunt Parameters
    <a href="/help/user_manual.html#hunt-parameters" target="_blank">
    <i class="glyphicon glyphicon-question-sign"></i></a>
  </h3>
  {{this.rendered_hunt_runner_args|safe}}

  {{this.rendered_hunt_args|safe}}
""")

  def Validate(self, request, response):
    pass

  def Layout(self, request, response, apply_template=None):
    response = super(HuntInformation, self).Layout(
        request, response, apply_template=apply_template)
    return self.CallJavascript(response,
                               "HuntInformation.Layout",
                               renderer=self.__class__.__name__)

  def RenderAjax(self, request, response):
    """Layout the hunt information."""
    parser = HuntArgsParser(request)
    self.hunt_runner_args = parser.ParseHuntRunnerArgs()
    self.hunt_args = parser.ParseHuntArgs()

    # Validate the hunt args.
    self.hunt_args.Validate()
    self.hunt_runner_args.Validate()

    # Render the protobufs nicely.
    self.rendered_hunt_args = renderers.RDFProtoRenderer(
        self.hunt_args).RawHTML(request)

    self.rendered_hunt_runner_args = renderers.RDFProtoRenderer(
        self.hunt_runner_args).RawHTML(request)

    return super(HuntInformation, self).Layout(
        request, response, apply_template=self.ajax_template)


class HuntRunStatus(HuntInformation):
  """Launches the hunt and displays status summary."""

  description = "Hunt was created."

  ajax_template = renderers.Template("""
<div class="HuntLaunchSummary padded">
  <p class="text-success">Hunt was created!</p>
</div>
""")

  failure_template = renderers.Template("""
<div class="Failure padded">
<p class="text-error">Failure: <span class="Reason">
  {{reason|escape}}</span></p>
</div>
""")

  def RenderAjax(self, request, response):
    """Attempt to run a CreateGenericHuntFlow."""
    parser = HuntArgsParser(request)
    try:
      hunt_runner_args = parser.ParseHuntRunnerArgs()
      hunt_runner_args.token = request.token

      hunt_args = parser.ParseHuntArgs()

      flow.GRRFlow.StartFlow(flow_name="CreateGenericHuntFlow",
                             hunt_runner_args=hunt_runner_args,
                             hunt_args=hunt_args,
                             token=request.token)

    except Exception as e:  # pylint: disable=broad-except
      logging.exception("Failed to create hunt: %s", e)
      return self.RenderFromTemplate(self.failure_template, response, reason=e)

    return super(HuntRunStatus, self).Layout(request,
                                             response,
                                             apply_template=self.ajax_template)


class NewHunt(wizards.WizardRenderer):
  """A wizard to create a new hunt."""
  render_as_modal = False
  wizard_name = "hunt_run"
  title = "New Hunt"
  pages = [
      HuntConfigureFlow,
      HuntConfigureOutputPlugins,
      ConfigureHuntRules,
      HuntInformation,
      HuntRunStatus,
  ]
