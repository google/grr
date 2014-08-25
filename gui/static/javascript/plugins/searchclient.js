var grr = window.grr || {};

/**
 * Namespace for the glob completer.
 */
grr.labels_completer = {};

/**
 * A filter function which matches the start of the completion list.
 *
 * @param {Array} completions the completion list
 * @param {string} term is the term to match.
 *
 * @return {Array} a list of matches.
 */
grr.labels_completer.filter = function(completions, term) {
  var matcher = new RegExp('^' + $.ui.autocomplete.escapeRegex(term), 'i');
  return $.grep(completions, function(value) {
    return matcher.test(value.label || value.value || value);
  });
};

/**
 * Build a completer on top of a text input.
 *
 * @param {string} dom_id is the DOM id of the text input field.
 * @param {Array} completions are possible completions.
 * @param {string} split_term is the term which triggers the completion.
 */
grr.labels_completer.Completer = function(dom_id, completions, split_term) {
  $('#' + dom_id).bind('keydown', function(event) {
    if (event.keyCode === $.ui.keyCode.TAB &&
        $(this).data('ui-autocomplete').menu.active) {
      event.preventDefault();
    }
  }).bind('focus', function(event) {
    if (!split_term) {
      $(this).autocomplete('search');
    }
  }).autocomplete({
    minLength: 0,
    source: function(request, response) {
      if (split_term) {
        var terms = request.term.split(split_term);
        if (terms.length % 2) {
          response([]);
        } else {
          response(grr.labels_completer.filter(completions, terms.pop()));
        }
      } else {
        response(grr.labels_completer.filter(completions, request.term));
      }
    },
    focus: function() {
      // prevent value inserted on focus
      return false;
    },
    select: function(event, ui) {
      if (split_term) {
        var terms = this.value.split(split_term);

        // remove the current input
        terms.pop();

        // add the selected item
        terms.push(ui.item.value);

        this.value = terms.join('label:');
        grr.forms.inputOnChange(this);
        return false;
      } else {
        return false;
      }
    }
  }).wrap('<abbr title="Type label: to open a list of possible ' +
      'labels completions."/>');
};

grr.Renderer('GlobExpressionFormRenderer', {
  Layout: function(state) {
  }
});


grr.Renderer('ContentView', {
  Layout: function(state) {
    var global_notification_poll_time = state.global_notification_poll_time;

    grr.canary_mode = state.canary_mode;

    if (grr.hash.c) {
      grr.state.client_id = grr.hash.c;
    }

    grr.poll('GlobalNotificationBar', 'global-notification',
             function(data) { // success handler
               $('#global-notification').html(data);
               $('#global-notification button.close').click(function() {
                 var notification_hash = $(this).attr('notification-hash');
                 grr.update('GlobalNotificationBar', null,
                            {notification_hash: notification_hash});

                 $(this).closest('.alert').alert('close');
               });
               return true;
             },
             global_notification_poll_time, {});
  }
});

grr.Renderer('Navigator', {
  Layout: function(state) {
    var unique = state.unique;
    var id = state.id;
    var renderer = state.renderer;
    var poll_time = state.poll_time;
    var client_id = state.client_id;

    grr.installNavigationActions('nav_' + unique);
    if (!grr.hash.main) {
      $('a[grrtarget=HostInformation]').click();
    } else {
      $('a[grrtarget=' + grr.hash.main + ']').click();
    }

    grr.poll('StatusRenderer', 'infoline_' + unique,
             function(data) {
               $('#infoline_' + unique).html(data);
               return true;
             }, poll_time, grr.state, null,
             function() {
               $('#infoline_' + unique).html('Client status not available.');
             });

    // Reload the navigator when a new client is selected.
    grr.subscribe('client_selection', function() {
      grr.layout(renderer, id);
    }, unique);

    if (grr.hash.c && grr.hash.c != client_id) {
      grr.publish('client_selection', grr.hash.c);
    }
  }
});

grr.Renderer('HostTable', {
  Layout: function(state) {
    var unique = state.unique;
    var id = state.id;

    // Receive the selection event and emit a client_id
    grr.subscribe('select_table_' + id, function(node) {
      var aff4_path = $('span[aff4_path]', node).attr('aff4_path');
      var cn = aff4_path.replace('aff4:/', '');
      grr.state.client_id = cn;
      grr.publish('hash_state', 'c', cn);

      // Clear the authorization for new clients.
      grr.publish('hash_state', 'reason', '');
      grr.state.reason = '';

      grr.publish('hash_state', 'main', null);
      grr.publish('client_selection', cn);
     }, unique);

    // Select-all checkbox.
    $('#' + unique + ' :checkbox[select_all_client_urns]').change(function() {
      var allCheckboxes = $('#' + unique + ' :checkbox[client_urn]');
      allCheckboxes.prop('checked', $(this).is(':checked'));
      allCheckboxes.trigger('change');
    });

    // Regular checbkoxes.
    var selectedClients = [];
    $('#' + unique + ' :checkbox[client_urn]').click(function(event) {
      event.stopPropagation();
    }).change(function() {
      var client_urn = $(this).attr('client_urn');

      if ($(this).is(':checked')) {
        if (selectedClients.indexOf(client_urn) == -1) {
          selectedClients.push(client_urn);
          selectedClients.sort();
        }
      } else {
        if (selectedClients.indexOf(client_urn) != -1) {
          selectedClients.splice(selectedClients.indexOf(client_urn), 1);
        }
      }
    });

    // Enabled buttons on action bar if something is selected
    var actionBar = $('#client_action_bar_' + unique);
    var prevState = {
      'selectedClients': []
    };
    grr.subscribe('timer', function() {
      if (prevState['selectedClients'] == selectedClients) {
        return;
      }
      prevState['selectedClients'] = selectedClients.slice();

      if (selectedClients.length) {
        actionBar.find('button').removeAttr('disabled');
      } else {
        actionBar.find('button').attr('disabled', 'true');
      }
    }, unique);

    // Apply Label renderer
    $('#apply_label_dialog_' + unique).on('show', function(event) {
      if (event.target != this) return;

      grr.layout('ApplyLabelToClientsDialog',
                 'apply_label_dialog_' + unique,
                 {'selected_clients': JSON.stringify(selectedClients)});
    }).on('hidden', function(event) {
      // Only refresh the view is labels were updated.
      if ($(this).data('updated')) {
        grr.layout('HostTable', 'main', {q: grr.hash['q']});
      }
      $(this).html('');
    });
  }
});

grr.Renderer('ApplyLabelToClientsDialog', {
  Layout: function(state) {
    grr.labels_completer.Completer('input_apply_label_to_clients',
                                   state.labels);
  },
  RenderAjax: function(state) {
    // Flag that labels were updated and we should refresh hosts view.
    $('#' + state.unique).closest(
        'div[name=ApplyLabelDialog]').data('updated', true);
  }
});

grr.Renderer('SearchHostView', {
  Layout: function(state) {
    grr.labels_completer.Completer('client_query', state.labels, /label:/);

    $('#search_host').submit(function() {
      var input = $('input[name="q"]').val();
      var sha_regex = /^[A-F0-9]{64}$/i;

      if (sha_regex.test(input)) {
        grr.layout('FilestoreTable', 'main', {q: input});
      } else {
        grr.publish('hash_state', 'main', 'HostTable');
        grr.publish('hash_state', 'q', input);
        grr.layout('HostTable', 'main', {q: input});
      }

      return false;
    });

    var searchInput = $('#search_host input[name=q]');
    if (grr.hash.main == 'HostTable' && grr.hash.q &&
        searchInput.val() != grr.hash.q) {
      searchInput.val(grr.hash.q);
      grr.layout('HostTable', 'main', {q: grr.hash.q});
    } else {
      searchInput.focus();
    }
  }
});

grr.Renderer('FrontPage', {
  Layout: function(state) {
    // Update main's state from the hash
    if (grr.hash.main) {
      grr.layout(grr.hash.main, 'main');
    }
  }
});
