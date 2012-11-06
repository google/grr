#!/usr/bin/env python
"""Implementation of "Launch Hunt" wizard."""


import json


from grr.gui import renderers
from grr.gui.plugins import flow_management
from grr.gui.plugins import foreman
from grr.lib import aff4
from grr.lib import flow
from grr.lib import type_info
from grr.lib import utils
from grr.lib.flows.general import hunts
from grr.proto import jobs_pb2


class LaunchHunts(renderers.WizardRenderer):
  """Launches a new hunt."""

  wizard_name = "hunt_run"
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
          description="Step 3. Review The Hunt And Test Its' Rules",
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

  layout_template = """
<div id="HuntConfigureFlow_{{unique|escape}}"></div>
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
  }, "HuntConfigureFlow_{{unique|escapejs}}");
</script>
""" + renderers.Splitter.layout_template


class HuntFlowForm(flow_management.FlowForm):
  """Flow configuration form that stores the data in wizard's DOM data."""

  # No need to avoid clashes, because the form by itself is not submitted, it's
  # only used by Javascript to form a JSON request.
  arg_prefix = ""

  layout_template = renderers.Template("""
<div class="HuntFormBody" id="FormBody_{{unique|escape}}">
<h1>{{this.flow_name|escape}}</h1>

{% if this.form_elements %}
  <table><tbody>
  {% for form_element in this.form_elements %}
    <tr>{{form_element|escape}}</tr>
  {% endfor %}
  </tbody></table>
{% else %}
  Nothing to configure.
{% endif %}
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
<script id="HuntsRulesModels_{{unique|escape}}" type="text/x-jquery-tmpl">
  <div class="Rule">
    {% for form_name, form in this.forms.items %}
      {% templatetag openvariable %}if rule_type == "{{form_name}}"
        {% templatetag closevariable %}
        <table name="{{form_name|escape}}"><tbody>
          <tr>
             <td>rule type</td>
             <td>
               <select name="rule_type">
                 {% for fn in this.forms.iterkeys %}
                   <option value="{{fn|escape}}"
                     {% if fn == form_name %}selected{% endif %}>
                     {{fn|escape}}
                   </option>
                 {% endfor %}
               </select>
             </td>
          </tr>
          {% for form_element in form %}
          <tr>{{form_element|escape}}</tr>
          {% endfor %}
        </tbody></table>
      {% templatetag openvariable %}/if{% templatetag closevariable %}
    {% endfor %}
    <input name="remove" type="button" value="Remove" />
  </div>
</script>

<div class="HuntConfigureRules">
  <div id="HuntsRules_{{unique|escape}}" class="RulesList"></div>
  <div class="AddButton">
    <input type="button" id="AddHuntRule_{{unique|escape}}" value="Add Rule" />
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
    $(":input", this).each(function() {
      attr_name = $(this).attr("name");

      if (rules[index][attr_name] != null) {
        $(this).val(rules[index][attr_name]);
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

  def RenderProtobufElements(self, pb):
    for field in pb.DESCRIPTOR.fields:
      if field.type == field.TYPE_STRING:
        tinfo = type_info.String()
      elif field.type == field.TYPE_UINT64:
        tinfo = type_info.Number()
      elif field.type == field.TYPE_ENUM:
        tinfo = type_info.ProtoEnum(pb, field.enum_type.name)
      else:
        tinfo = None

      if not tinfo:
        continue
      form_renderer = renderers.Renderer.classes[tinfo.renderer]()
      yield form_renderer.Format(field=field.name, arg_type=tinfo,
                                 value=getattr(pb, field.name),
                                 desc=field.name)

  def Layout(self, request, response):
    self.forms = {
        "ForemanAttributeRegex": self.RenderProtobufElements(
            jobs_pb2.ForemanAttributeRegex()),
        "ForemanAttributeInteger": self.RenderProtobufElements(
            jobs_pb2.ForemanAttributeInteger())
        }

    return renderers.TemplateRenderer.Layout(self, request, response)


class HuntRequestParsingMixin(object):
  """Mixin with hunt's JSON configuration parsing methods."""

  def ParseFlowConfig(self, flow_class, flow_args_json):
    """Parse flow config JSON."""

    result = {}
    for arg_name, arg_type, arg_default in flow_class.GetFlowArgTypeInfo():
      if arg_name in flow_args_json:
        val = arg_type.DecodeString(flow_args_json[arg_name])
      else:
        val = arg_default
      result[arg_name] = val

    return result

  def ParseHuntRules(self, hunt_rules_json):
    """Parse rules config JSON."""

    result = []
    for rule_json in hunt_rules_json:
      if rule_json["rule_type"] == "ForemanAttributeRegex":
        rule_pb = jobs_pb2.ForemanAttributeRegex()
      elif rule_json["rule_type"] == "ForemanAttributeInteger":
        rule_pb = jobs_pb2.ForemanAttributeInteger()
      else:
        raise RuntimeError("Unknown rule type: " + rule_json["rule_type"])

      for field in rule_pb.DESCRIPTOR.fields:
        if not field.name in rule_json:
          continue

        if field.type == field.TYPE_STRING:
          tinfo = type_info.String()
        elif field.type == field.TYPE_UINT64:
          tinfo = type_info.Number()
        elif field.type == field.TYPE_ENUM:
          tinfo = type_info.ProtoEnum(rule_pb, field.enum_type.name)
        else:
          raise RuntimeError("Unknown field type: " + field.type)

        setattr(rule_pb, field.name, tinfo.DecodeString(rule_json[field.name]))

      result.append(rule_pb)

    return result

  def GetHuntFromRequest(self, request):
    """Parse JSON'ed hunt configuration from request into hunt object."""

    hunt_config_json = request.REQ.get("hunt_run")
    hunt_config = json.loads(hunt_config_json)

    flow_name = hunt_config["hunt_flow_name"]
    flow_config_json = hunt_config.get("hunt_flow_config", {})
    rules_config_json = hunt_config["hunt_rules_config"]

    flow_class = flow.GRRFlow.classes[flow_name]
    flow_config = self.ParseFlowConfig(flow_class, flow_config_json or {})
    rules_config = self.ParseHuntRules(rules_config_json)

    generic_hunt = hunts.GenericHunt(flow_name, flow_config,
                                     token=request.token)
    generic_hunt.AddRule(rules_config)

    return generic_hunt


class HuntRuleInformation(foreman.ReadOnlyForemanRuleTable,
                          HuntRequestParsingMixin):
  """Renders hunt's rules table, getting rules configuration from request."""

  def Layout(self, request, response):
    # We have to explicitly preserve "hunt_run" request variable in the state
    # so that it would be passed in the request to RenderAjax handler.
    self.state["hunt_run"] = request.REQ.get("hunt_run", "")
    return foreman.ReadOnlyForemanRuleTable.Layout(self, request, response)

  def RenderAjax(self, request, response):
    hunt = self.GetHuntFromRequest(request)
    for rule in hunt.rules:
      self.AddRow(dict(Created=aff4.RDFDatetime(rule.created),
                       Expires=aff4.RDFDatetime(rule.expires),
                       Description=rule.description,
                       Rules=rule,
                       Actions=rule))

    return renderers.TableRenderer.RenderAjax(self, request, response)


class HuntInformation(renderers.TemplateRenderer, HuntRequestParsingMixin):
  """Displays information about a hunt: flow settings and rules."""

  failure_reason = None
  failure_template = renderers.Template("""
<div class="Failure">
Failure due: <span class="Reason">{{this.failure_reason|escape}}</span>
</div>
""")

  layout_template = renderers.Template("""
<div class="HuntInformation" id="HuntInformation_{{unique|escape}}">
  <div class="Flow">
    <h1>{{this.hunt.flow_name|escape}}</h1>

    {% if this.hunt.flow_args %}
      <h2>Settings</h2>
      <table class="attributesTable">
        <thead class="attributesTableHeader">
          <tr><th>Attribue</th><th>Value</th></tr>
        </thead>
        <tbody class="attributesTableContent">
          {% for key,value in this.hunt.flow_args.iteritems %}
          <tr>
            <td>{{key|escape}}</td><td>{{value|escape}}</td>
          </tr>
        {% endfor %}
        </tbody>
      </table>
    {% endif %}
  </div>

  <!-- Classes inherited from HuntInformation may fill this div with
  something. -->
  <div class="Misc"></div>

  <h2>Rules</h2>
  <div id="HuntRuleInformation_{{unique|escape}}" class="Rules"></div>
</div>

<script>
(function() {
  var wizardState = $("#HuntInformation_{{unique|escapejs}}").
    closest(".Wizard").data();

  grr.layout("HuntRuleInformation",
    "HuntRuleInformation_{{unique|escapejs}}",
    {"hunt_run": JSON.stringify(wizardState)},
    function() {
      // Hack - delete all explicitly set "height" values - we want the table
      // to be flexible and to expand automatically
      $("#HuntRuleInformation_{{unique|escapejs}} *").css("height", "auto");
    }
  );
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

  ajax_template = renderers.Template("""
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

  def RenderAjax(self, request, response):
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

    self.all_clients = 0
    self.num_matching_clients = 0
    matching_clients = []
    for client in root.OpenChildren(chunk_limit=100000):
      self.all_clients += 1
      if generic_hunt.CheckClient(client):
        self.num_matching_clients += 1
        matching_clients.append(utils.SmartUnicode(client.urn))

    self.matching_clients = matching_clients[:3]
    return renderers.TemplateRenderer.Layout(self, request, response,
                                             apply_template=self.ajax_template)

  def Layout(self, request, response):
    # We have to explicitly preserve "hunt_run" request variable in the state
    # so that it would be passed in the request to RenderAjax handler.
    self.state["hunt_run"] = request.REQ.get("hunt_run", "")
    return HuntInformation.Layout(self, request, response)


class HuntRunStatus(HuntInformation):
  """Launches the hunt and displays status summary."""

  layout_template = renderers.Template("""
<div class="HuntLaunchSummary">
  <h1>Hunt was scheduled!</h1>
</div>
</script>
""")

  def Layout(self, request, response):
    hunt = self.GetHuntFromRequest(request)

    try:
      hunt.Run()
    except RuntimeError, e:
      return self.Fail(e, request, response)

    return HuntInformation.Layout(self, request, response)
