var grr = window.grr || {};

/**
 * Namespace for the glob completer.
 */
grr.glob_completer = {};

/**
 * A filter function which matches the start of the completion list.
 *
 * @param {Array} completions the completion list
 * @param {string} term is the term to match.
 *
 * @return {Array} a list of matches.
 */
grr.glob_completer.filter = function(completions, term) {
  var matcher = new RegExp('^' + $.ui.autocomplete.escapeRegex(term), 'i');
  return $.grep(completions, function(value) {
    return matcher.test(value.label || value.value || value);
  });
};

/**
 * Build a completer on top of a text input.
 *
 * @param {string|Element} element is the DOM id of the text input field or the
 *     DOM element itself.
 * @param {Array} completions are possible completions for %% sequences.
 */
grr.glob_completer.Completer = function(element, completions) {
  if (angular.isString(element)) {
    element = $('#' + element);
  }
  element.bind('keydown', function(event) {
    if (event.keyCode === $.ui.keyCode.TAB &&
        $(this).data('ui-autocomplete').menu.active) {
      event.preventDefault();
    }
  }).autocomplete({
    minLength: 0,
    source: function(request, response) {
      var terms = request.term.split(/%%/);
      if (terms.length % 2) {
        response([]);
      } else {
        response(grr.glob_completer.filter(completions, terms.pop()));
      }
    },
    focus: function() {
      // prevent value inserted on focus
      return false;
    },
    select: function(event, ui) {
      var terms = this.value.split(/%%/);

      // remove the current input
      terms.pop();

      // add the selected item
      terms.push(ui.item.value);
      terms.push('');

      this.value = terms.join('%%');
      // Angular code has to be notificed of the change.
      $(this).change();

      if ($(this).attr('id')) {
        grr.forms.inputOnChange(this);
      }
      return false;
    }
  }).wrap('<abbr title="Type %% to open a list of possible completions."/>');
};

grr.Renderer('GlobExpressionFormRenderer', {
  Layout: function(state) {
    grr.glob_completer.Completer(state.prefix, state.completions);
  }
});

grr.Renderer('FlowManagementTabs', {
  Layout: function(state) {
    var unique = state.unique;

    grr.subscribe('flow_select', function(path) {
      $('#' + unique).data().state.flow_path = path;
      $('#' + unique + ' li.active a').click();
    }, unique);
  }
});

grr.Renderer('SemanticProtoFlowForm', {
  Layout: function(state) {
    var unique = state.unique;
    var renderer = state.renderer;
    var id = state.id;

    $('#submit_' + unique).click(function() {
      var state = {};
      $.extend(state, $('#form_' + unique).data(), grr.state);
      grr.update(renderer, 'contents_' + unique, state);
      return false;
    });

    grr.subscribe('flow_select', function(path) {
      grr.layout(renderer, id, {
        flow_path: path,
        client_id: grr.state.client_id,
        reason: grr.state.reason
      });
    }, unique);
  },

  RenderAjax: function(state) {
    var dom_node = state.dom_node;
    var unique = state.unique;
    var renderer = state.renderer;
    var id = state.id;

    $('#' + dom_node + ' .FormBody').html('');

    grr.subscribe('flow_select', function(path) {
      grr.layout(renderer, id, {
        flow_path: path,
        client_id: grr.state.client_id,
        reason: grr.state.reason
      });
    }, unique);
  },

  RenderAjaxError: function(state) {
    grr.publish('grr_messages', { message: state.error, traceBack: state.error });
  }
});

grr.Renderer('FlowTabView', {
  Layout: function(state) {
    var unique = state.unique;
    var id = state.id;
    var renderer = state.renderer;

    grr.subscribe('flow_table_select', function(path) {
      grr.layout(renderer, id, {flow: path, client_id: grr.state.client_id});
    }, 'tab_contents_' + unique);
  }
});

grr.Renderer('ListFlowsTable', {
  Layout: function(state) {
    var unique = state.unique;
    var id = state.id;
    var selection_publish_queue = state.selection_publish_queue;

    $('#cancel_flow_' + unique).click(function() {
      // Find all selected rows and cancel them.
      $('#table_' + id).find('tr.row_selected div[flow_id]')
          .each(function() {
            var flow_id = $(this).attr('flow_id');
            var flow_div_id = $(this).attr('id');

            /* Cancel the flow, and then reset the icon. */
            grr.layout(
                'FlowFormCancelAction', flow_div_id, {flow_id: flow_id},
                function() { $('#table_' + id).trigger('refresh'); });
          });
    });

    //Receive the selection event and emit a session_id
    grr.subscribe('select_table_' + id, function(node) {
      if (node) {
        flow = node.find('div[flow_id]').attr('flow_id');
        if (flow) {
          grr.publish(selection_publish_queue, flow);
        }
      }
    }, unique);

    // Update the flow view from the hash.
    if (grr.hash.flow) {
      // This is needed for cases when flow list and flow information are
      // rendered as parts of the same renderer. In that case the
      // ShowFlowInformation renderer won't be able to react on the
      // click because it subscribes for the flow_table_select event after
      // the code below is executed.
      grr.subscribe('on_renderer_load', function(rendererId) {
        // on_renderer_load is called for renderers loaded through
        // grr.layout and grr.update. No 'on_renderer_load' message will be
        // published for renderers that are renderered as part of other
        // renderers. Therefore we check here if we belong to the loaded
        // renderer's tree.
        if (unique == rendererId ||
            $('#' + unique).parents('#' + rendererId).length > 0) {
          $('div[flow_id="' + grr.hash.flow + '"]').parents('tr').click();
        }
      }, unique);
    }
  }
});

grr.Renderer('FlowPBRenderer', {
  RenderBacktrace: function() {
    var name = state.name;

    $('#hidden_pre_' + name).click(function() {
      $(this).find('ins').toggleClass('ui-icon-plus ui-icon-minus');
      $(this).find('.contents').toggle();
    }).click();
  }
});

grr.Renderer('FlowNotificationRenderer', {
  Layout: function(state) {
    var unique = state.unique;

    $('#' + unique).click(function() {
      grr.loadFromHash($(this).attr('target_hash'));
    });
  }
});
