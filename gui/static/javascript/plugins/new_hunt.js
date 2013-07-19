var grr = window.grr || {};

grr.Renderer('NewHunt', {
  Layout: function(state) {
    $('#Wizard_' + state['unique']).data({
      hunt_flow_name: null,
      hunt_flow_config: {},
      hunt_output_config: [{
        output_type: 'CollectionPlugin'
      }],
      hunt_rules_config: [{
        rule_type: 'Windows systems'
      }]
    });
  }
});

grr.Renderer('HuntConfigureFlow', {
  Layout: function(state) {
    // Attaching subscribe('flow_select') to the div with unique id to avoid
    // multiple listeners being subscribed at the same time. When this div
    // goes away, the listener won't fire anymore. This is exactly what happens
    // when we press Next and then Back in the wizard. Splitter gets regenerated
    // with the same id, but with different unique id.
    grr.subscribe('flow_select', function(path) {
      grr.layout('HuntFlowForm',
                 state['id'] + '_rightPane',
                 { flow_name: path });
    }, state['id']);
  }
});

grr.Renderer('HuntFlowForm', {
  Layout: function(state) {
    var formBodyId = 'FormBody_' + state['unique'];
    var flowDescriptionId = 'FlowDescription_' + state['unique'];

    // Show flow description via AJAX call.
    grr.layout('FlowInformation', flowDescriptionId,
               {flow_path: state['flow_name'], no_header: true});

    var wizardState = $('#' + formBodyId).closest('.Wizard').data();

    // If selected flow changed, we should reset the state in
    // wizardState["hunt_flow_config"]. Otherwise, we should fill the input
    // elements with the data that we keep in wizardState["hunt_flow_config"].
    var shouldResetValues = (wizardState['hunt_flow_name'] !=
        state['flow_name']);

    if (shouldResetValues) {
      wizardState['hunt_flow_name'] = state['flow_name'];
      wizardState['hunt_flow_config'] = {};
    } else {
      grr.update_form(formBodyId, wizardState['hunt_flow_config']);

      // Checkboxes are different from other input elements. We should
      // explicitly set their "checked" property if their value is True.
      $('#' + formBodyId + ' :checkbox').each(function() {
        $(this).prop('checked', $(this).val() == 'True');
      });
    }

    // Fixup checkboxes so they return values even if unchecked.
    $('#' + formBodyId + ' input[type=checkbox]').change(function() {
      $(this).attr('value', $(this).attr('checked') ? 'True' : 'False');
    });

    $('input.form_field_or_none').each(function(index) {
      grr.formNoneHandler($(this));
    });

    // Update our wizard's state when any input changes. Checkboxes will also
    // work, because we change their value when they're checked/unchecked (see
    // corresponding change() handler above).
    $('#' + formBodyId + ' :input').change(function() {
      wizardState['hunt_flow_config'][$(this).attr('name')] = $(this).val();
    });
    $('#' + formBodyId + ' :input').change();
  }
});

// TODO: This is very similar to the rules rendering below. We should
// make one generic function and reuse it at some point.
grr.Renderer('HuntConfigureOutput', {
  Layout: function(state) {
    var huntsOutputId = '#HuntsOutputs_' + state['unique'];
    var huntsOutputModelsId = '#HuntsOutputModels_' + state['unique'];

    var wizardState = $(huntsOutputId).closest('.Wizard').data();
    var outputs = wizardState['hunt_output_config'];

    // This function updates the whole list of outputs. We call it
    // when an output is added or removed, or when an output's type changes.
    var updateOutputs = function() {
      var outputDiv = $(huntsOutputId);
      outputDiv.html('');
      $(huntsOutputModelsId).tmpl(outputs).appendTo(outputDiv);

      $(huntsOutputId + ' div.Rule').each(function(index) {
        // Update wizard's state when input's value changes.
        $(':input', this).change(function() {
          var value = $(this).val();
          var name = $(this).attr('name');
          outputs[index][name] = value;
          if (name == 'output_type') {
            outputs[index] = {output_type: value};
            updateOutputs();
          }
        });

        // Fill input elements for this plugin with the data that we have.
        // If we don't have the data, then do the reverse thing - put value
        // from the input element into our data structure.
        $(':input', this).each(function() {
          attr_name = $(this).attr('name');

          if (outputs[index][attr_name] != null) {
            $(this).val(outputs[index][attr_name]);
          } else {
            outputs[index][attr_name] = $(this).val();
          }
        });

        if (outputs.length > 1) {
          $(":button[name='remove']", this).click(function() {
            outputs.splice(index, 1);
            updateOutputs();
          });
        } else {
          $(":button[name='remove']", this).hide();
        }
      });
    };

    $('#AddHuntOutput_' + state['unique']).click(function() {
      outputs.push({output_type: 'CollectionPlugin'});
      updateOutputs();
    });

    updateOutputs();
  }
});

grr.Renderer('HuntConfigureRules', {
  Layout: function(state) {
    var huntsRulesId = '#HuntsRules_' + state['unique'];
    var huntsRulesModelsId = '#HuntsRulesModels_' + state['unique'];

    var wizardState = $(huntsRulesId).closest('.Wizard').data();
    var rules = wizardState['hunt_rules_config'];

    // This function updates the whole list of rules. We call it when rules is
    // added or removed, or when rule's type changes.
    var updateRules = function() {
      var rulesDiv = $(huntsRulesId);
      rulesDiv.html('');
      $(huntsRulesModelsId).tmpl(rules).appendTo(rulesDiv);

      $(huntsRulesId + ' div.Rule').each(function(index) {
        // Update wizard's state when input's value changes.
        $(':input', this).change(function() {
          var value = $(this).val();
          var name = $(this).attr('name');
          rules[index][name] = value;
          if (name == 'rule_type') {
            rules[index] = {rule_type: value};
            updateRules();
          }
        });

        // Fill input elements for this rule with the data that we have.
        // If we don't have the data, then do the reverse thing - put value
        // from the input element into our data structure.
        $(':input', this).each(function() {
          attr_name = $(this).attr('name');

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
    };

    $('#AddHuntRule_' + state['unique']).click(function() {
      rules.push({rule_type: 'Windows systems'});
      updateRules();
    });

    updateRules();
  }
});

grr.Renderer('HuntInformation', {
  Layout: function(state) {
    var wizardState = $('#HuntInformation_' + state['unique']).
        closest('.Wizard').data();

    grr.layout('HuntRuleInformation',
               'HuntRuleInformation_' + state['unique'],
               {'hunt_run': JSON.stringify(wizardState)});
  }
});
