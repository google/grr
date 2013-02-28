#!/usr/bin/env python
"""Implementation of "Launch Hunt" wizard."""


import json


from grr.gui import renderers
from grr.gui.plugins import flow_management
from grr.gui.plugins import foreman
from grr.lib import aff4
from grr.lib import flow
from grr.lib import hunts
from grr.lib import rdfvalue
from grr.lib import type_info
from grr.lib import utils


class LaunchHunts(renderers.WizardRenderer):
  """Launches a new hunt."""

  wizard_name = "hunt_run"
  title = "Launch Hunt"
  pages = [
      renderers.WizardPage(
          name="ConfigureFlow",
          description="Step 1. Select And Configure The Flow",
          renderer="HuntConfigureFlow"),
      renderers.WizardPage(
          name="ConfigureRules",
          description="Step 2. Configure Hunt Rules",
          renderer="HuntConfigureRules"),
      renderers.WizardPage(
          name="ReviewAndTest",
          description="Step 3. Review The Hunt",
          renderer="HuntReviewAndTest",
          next_button_label="Run",
          wait_for_event="HuntTestPerformed"),
      renderers.WizardPage(
          name="Done",
          description="Done!",
          renderer="HuntRunStatus",
          next_button_label="Done",
          show_back_button=False)
      ]

  layout_template = renderers.WizardRenderer.layout_template + """
<script>
(function() {
  $("#Wizard_{{unique|escapejs}}").data({hunt_flow_name: null,
    hunt_flow_config: {},
    hunt_rules_config: [{
      rule_type: "ForemanAttributeRegex"
    }]
  });
})();
</script>
"""


class HuntConfigureFlow(renderers.Splitter):
  """Configure hunt's flow."""

  left_renderer = "FlowTree"
  top_right_renderer = "HuntFlowForm"
  bottom_right_renderer = "FlowManagementTabs"

  min_left_pane_width = 200

  layout_template = renderers.Splitter.layout_template + """
<script>
  // Attaching subscribe('flow_select') to the div with unique id to avoid
  // multiple listeners being subscribed at the same time. When this div
  // goes away, the listener won't fire anymore. This is exactly what happens
  // when we press Next and then Back in the wizard. Splitter gets regenerated
  // with the same id, but with different unique id.
  grr.subscribe('flow_select', function(path) {
    grr.layout("HuntFlowForm",
      "{{id|escapejs}}_rightTopPane",
      { flow_name: path });
  }, "{{id|escapejs}}");
</script>
"""


class HuntFlowForm(flow_management.FlowForm):
  """Flow configuration form that stores the data in wizard's DOM data."""

  # No need to avoid clashes, because the form by itself is not submitted, it's
  # only used by Javascript to form a JSON request.
  prefix = ""

  # There's no sense in displaying "Notify at Completion" argument when
  # configuring hunts
  ignore_flow_args = ["notify_to_user"]

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
<div class="control-group">
  <label class="control-label">Client Limit</label>
  <div class="controls">
    <input type="text" name="client_limit" value="" />
  </div>
</div>
<div class="control-group">
  <label class="control-label">Expiration Time (try s,m,h,d)</label>
  <div class="controls">
    <input type="text" name="expiry_time" value="31d" />
  </div>
</div>
</form>

</div>

{% if this.flow_name %}
<script>
(function() {
  var wizardState = $("#FormBody_{{unique|escapejs}}").
    closest(".Wizard").data()

  // If selected flow changed, we should reset the state in
  // wizardState["hunt_flow_config"]. Otherwise, we should fill the input
  // elements with the data that we keep in wizardState["hunt_flow_config"].
  var shouldResetValues = (wizardState["hunt_flow_name"] !=
    "{{this.flow_name|escapejs}}");

  if (shouldResetValues) {
    wizardState["hunt_flow_name"] = "{{this.flow_name|escapejs}}";
    wizardState["hunt_flow_config"] = {}
  } else {
    grr.update_form("FormBody_{{unique|escape}}",
      wizardState["hunt_flow_config"]);

    // Checkboxes are different from other input elements. We should
    // explicitly set their "checked" property if their value is True.
    $('#FormBody_{{unique|escape}} :checkbox').each(function() {
      $(this).prop("checked", $(this).val() == "True");
    });
  }

  // Fixup checkboxes so they return values even if unchecked.
  $("#FormBody_{{unique|escape}} input[type=checkbox]").change(function() {
    $(this).attr("value", $(this).attr("checked") ? "True" : "False");
  });

  $("input.form_field_or_none").each(function(index) {
    grr.formNoneHandler($(this));
  });

  // Update our wizard's state when any input changes. Checkboxes will also
  // work, because we change their value when they're checked/unchecked (see
  // corresponding change() handler above).
  $("#FormBody_{{unique|escape}} :input").change(function() {
    wizardState["hunt_flow_config"][$(this).attr("name")] = $(this).val();
  });
  $("#FormBody_{{unique|escape}} :input").change();
})();
</script>
{% endif %}
""")


# TODO(user): we should have RDFProtoEditableRenderer or the likes to have
# a generic way of displaying forms for editing protobufs. Maybe it should be
# based on RDFProtoRenderer code.
class HuntConfigureRules(renderers.TemplateRenderer):
  """Configure hunt's rules."""

  # We generate jQuery template for different kind of rules that we have (i.e.
  # ForemanAttributeInteger, ForemanAttributeRegex). For every
  # cloned rule form, we register "change" event listener, which updates
  # wizard's configuration (by convention stored in wizard's DOM by using
  # jQuery.data()).
  layout_template = renderers.Template("""
{{this.hunt_form|safe}}

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

<script>
(function() {

var wizardState = $("#HuntsRules_{{unique|escapejs}}").closest(".Wizard").data()
var rules = wizardState["hunt_rules_config"];

// This function updates the whole list of rules. We call it when rules is
// added or removed, or when rule's type changes.
function updateRules() {
  var rulesDiv = $("#HuntsRules_{{unique|escapejs}}")
  rulesDiv.html("")
  $("#HuntsRulesModels_{{unique|escapejs}}").tmpl(rules).appendTo(rulesDiv);

  $("#HuntsRules_{{unique|escapejs}} div.Rule").each(function(index) {
    // Update wizard's state when input's value changes.
    $(":input", this).change(function() {
      var value = $(this).val();
      var name = $(this).attr("name");
      rules[index][name] = value;
      if (name == "rule_type") {
        rules[index] = {rule_type: value};
        updateRules();
      }
    });

    // Fill input elements for this rule with the data that we have.
    // If we don't have the data, then do the reverse thing - put value
    // from the input element into our data structure.
    $(":input", this).each(function() {
      attr_name = $(this).attr("name");

      if (rules[index][attr_name] != null) {
        $(this).val(rules[index][attr_name]);
      } else {
        rules[index][attr_name] = $(this).val();
      }
    });

    if (rules.length > 1) {
      $(":button[name='remove']", this).click(function() {
        rules.splice(index, 1);
        updateRules();
      });
    } else {
      $(":button[name='remove']", this).hide();
    }
  });
}

$("#AddHuntRule_{{unique|escapejs}}").click(function() {
  rules.push({rule_type: "ForemanAttributeRegex"});
  updateRules();
});

updateRules();

})();
</script>
""")

  def Layout(self, request, response):
    """Layout hunt rules."""
    type_descriptor_renderer = renderers.TypeDescriptorSetRenderer()

    regex_form = type_descriptor_renderer.Form(
        type_info.TypeDescriptorSet(type_info.ForemanAttributeRegexType()),
        request, prefix="")
    int_form = type_descriptor_renderer.Form(
        type_info.TypeDescriptorSet(type_info.ForemanAttributeIntegerType()),
        request, prefix="")

    self.forms = {"ForemanAttributeRegex": regex_form,
                  "ForemanAttributeInteger": int_form}

    return super(HuntConfigureRules, self).Layout(request, response)


class EmptyRequest(object):
  pass


class HuntRequestParsingMixin(object):
  """Mixin with hunt's JSON configuration parsing methods."""

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

    request = EmptyRequest()
    request.REQ = flow_args_json  # pylint: disable=g-bad-name
    flow_config = rdfvalue.RDFProtoDict(
        initializer=dict(type_descriptor_renderer.ParseArgs(
            tinfo, request, prefix="")))
    return flow_config

  def ParseHuntRules(self, hunt_rules_json):
    """Parse rules config JSON."""

    type_descriptor_renderer = renderers.TypeDescriptorSetRenderer()
    result = []
    for rule_json in hunt_rules_json:
      if rule_json["rule_type"] == "ForemanAttributeRegex":
        tinfo = type_info.TypeDescriptorSet(
            type_info.ForemanAttributeRegexType())
      elif rule_json["rule_type"] == "ForemanAttributeInteger":
        tinfo = type_info.TypeDescriptorSet(
            type_info.ForemanAttributeIntegerType())
      else:
        raise RuntimeError("Unknown rule type: " + rule_json["rule_type"])

      request = EmptyRequest()
      request.REQ = rule_json
      parse_result = dict(type_descriptor_renderer.ParseArgs(
          tinfo, request, prefix=""))

      rdf_rule = parse_result["foreman_attributes"]
      result.append(rdf_rule)

    return result

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

  def GetHuntFromRequest(self, request):
    """Parse JSON'ed hunt configuration from request into hunt object."""

    hunt_config_json = request.REQ.get("hunt_run")
    hunt_config = json.loads(hunt_config_json)

    flow_name = hunt_config["hunt_flow_name"]
    flow_config_json = hunt_config.get("hunt_flow_config", {})
    rules_config_json = hunt_config["hunt_rules_config"]

    expiry_time = self.ParseExpiryTime(flow_config_json["expiry_time"])
    client_limit = None
    if flow_config_json["client_limit"]:
      client_limit = int(flow_config_json["client_limit"])

    flow_class = flow.GRRFlow.classes[flow_name]
    flow_config = self.ParseFlowConfig(flow_class, flow_config_json or {})
    rules_config = self.ParseHuntRules(rules_config_json)

    generic_hunt = hunts.GenericHunt(flow_name=flow_name, args=flow_config,
                                     client_limit=client_limit,
                                     expiry_time=expiry_time,
                                     token=request.token)

    generic_hunt.AddRule(rules=rules_config)

    return generic_hunt


class HuntRuleInformation(foreman.ReadOnlyForemanRuleTable,
                          HuntRequestParsingMixin):
  """Renders hunt's rules table, getting rules configuration from request."""

  post_parameters = ["hunt_run"]

  def RenderAjax(self, request, response):
    hunt = self.GetHuntFromRequest(request)
    for rule in hunt.rules:
      self.AddRow(dict(Created=rdfvalue.RDFDatetime(rule.created),
                       Expires=rdfvalue.RDFDatetime(rule.expires),
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
  <div class="Flow">
    <h3>{{this.hunt.flow_name|escape}}</h3>

    {% if this.hunt.flow_args %}
      <h4>Settings</h4>
      <dl class="dl-horizontal">
        {% for key,value in this.hunt.flow_args.iteritems %}
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

  <h3>Rules</h3>
  <div id="HuntRuleInformation_{{unique|escape}}" class="Rules"></div>
</div>

<script>
(function() {
  var wizardState = $("#HuntInformation_{{unique|escapejs}}").
    closest(".Wizard").data();

  grr.layout("HuntRuleInformation",
    "HuntRuleInformation_{{unique|escapejs}}",
    {"hunt_run": JSON.stringify(wizardState)});
})();
</script>
""")

  def Fail(self, reason, request, response):
    """Render failure_template instead of layout_template."""

    self.failure_reason = reason
    return renderers.TemplateRenderer.Layout(
        self, request, response, apply_template=self.failure_template)

  def Layout(self, request, response):
    try:
      self.hunt = self.GetHuntFromRequest(request)
    except RuntimeError, e:
      return self.Fail(e, request, response)

    return renderers.TemplateRenderer.Layout(self, request, response)


class HuntReviewAndTest(HuntInformation):
  """Runs hunt's tests and displays the results."""

  clients_list_template = renderers.Template("""
<h2>Rules Testing Results</h2>
{% if this.display_warning %}
  Warning! One or more rules use a relative path under the client,
  this is not supported, so your count may be off.
{% endif %}

<br/>
Out of {{ this.all_clients }} checked clients,
{{ this.num_matching_clients }} matched the given rule set.
<br/>

Example matches:
<ul>
  {% for client in this.matching_clients %}
  <li>{{client|escape}}</li>
  {% endfor %}
</ul>
</div>

<script>
  grr.publish("WizardProceed", "HuntTestPerformed");
</script>
""")

  rules_testing_template = renderers.Template("""
<!-- TODO(mbushkov): implement hunt rules' testing. !-->
<!-- Hunt's rules were tested successfully. -->

<script>
  grr.publish("WizardProceed", "HuntTestPerformed");
</script>
""")

  layout_template = """
<div id="TestsInProgress_{{unique|escape}}" class="TestsInProgress">
  <h2>Rules Testing Results</h2>
  Please wait... Rules testing in progress...
</div>

<script>
(function() {

$("#TestsInProgress_{{unique|escapejs}}").appendTo(
  $("#HuntInformation_{{unique|escapejs}} .Misc"));
grr.update("HuntReviewAndTest", "TestsInProgress_{{unique|escapejs}}",
  {{this.state_json|safe}});

})();
</script>

""" + HuntInformation.layout_template

  post_parameters = ["hunt_run"]

  # TODO(user): optimize or get rid of this function.
  def RenderMatchingClientslist(self, request, response):
    """Run hunt's rules test and render testing summary."""
    try:
      generic_hunt = self.GetHuntFromRequest(request)
    except RuntimeError, e:
      return self.Fail(e, request, response)

    root = aff4.FACTORY.Open(aff4.ROOT_URN, token=request.token)
    self.display_warning = False
    for rule in generic_hunt.rules:
      for r in rule.regex_rules:
        if r.path != "/":
          self.display_warning = True
      for r in rule.integer_rules:
        if r.path != "/":
          self.display_warning = True

    # Filtering out non-clients to avoid UnauthorizedAccess exceptions
    clients = []
    for urn in root.ListChildren():
      if aff4.AFF4Object.VFSGRRClient.CLIENT_ID_RE.match(urn.Basename()):
        clients.append(urn)

    self.all_clients = 0
    self.num_matching_clients = 0
    matching_clients = []
    for client in aff4.FACTORY.MultiOpen(clients, token=request.token):
      self.all_clients += 1
      if generic_hunt.CheckClient(client):
        self.num_matching_clients += 1
        matching_clients.append(utils.SmartUnicode(client.urn))

    self.matching_clients = matching_clients[:3]
    return renderers.TemplateRenderer.Layout(self, request, response,
                                             apply_template=self.ajax_template)

  def RenderAjax(self, request, response):
    return renderers.TemplateRenderer.Layout(
        self, request, response, apply_template=self.rules_testing_template)


class HuntRunStatus(HuntInformation):
  """Launches the hunt and displays status summary."""

  layout_template = renderers.Template("""
<div class="HuntLaunchSummary padded">
  <p class="text-success">Hunt was scheduled!</p>
</div>
</script>
""")

  def Layout(self, request, response):
    """Attempt to run a CreateAndRunGenericHuntFlow."""
    hunt = self.GetHuntFromRequest(request)

    try:
      hunt_rules = []
      for r in hunt.rules:
        hunt_rules.extend(r.regex_rules)
        hunt_rules.extend(r.integer_rules)

      flow.FACTORY.StartFlow(None, "CreateAndRunGenericHuntFlow",
                             token=request.token,
                             expiry_time=hunt.expiry_time,
                             client_limit=hunt.client_limit,
                             hunt_flow_name=hunt.flow_name,
                             hunt_flow_args=hunt.args,
                             hunt_rules=hunt_rules)
    except RuntimeError, e:
      return self.Fail(e, request, response)

    return HuntInformation.Layout(self, request, response)
