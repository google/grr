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
 * @param {string|Element} element is the DOM id of the text input field or the
 *     DOM element itself.
 * @param {Array} completions are possible completions.
 * @param {string} split_term is the term which triggers the completion.
 */
grr.labels_completer.Completer = function(element, completions, split_term) {
  if (angular.isString(element)) {
    element = $('#' + element);
  }
  element.bind('keydown', function(event) {
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
        terms = grr.labels_completer.filter(completions, request.term);
        if ($.inArray(request.term, terms) != -1) {
          response([]);
        }
        else {
          response(terms);
        }
      }
    },
    focus: function() {
      // prevent value inserted on focus
      return false;
    },
    select: function(event, ui) {
      var terms = this.value.split(split_term);

      // remove the current input
      terms.pop();

      // add the selected item
      terms.push(ui.item.value);

      this.value = terms.join('label:');

      // Angular code has to be notificed of the change.
      $(this).change();

      // Id will only be set in legacy code.
      if ($(this).attr('id')) {
        grr.forms.inputOnChange(this);
      }

      event.preventDefault();
      return false;
    }
  });
};

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

    // Reload the navigator when a new hunt is selected.
    grr.subscribe('hunt_selection', function() {
      grr.layout(renderer, id);
    }, unique);

    if (grr.hash.c && grr.hash.c != client_id) {
      grr.publish('client_selection', grr.hash.c);
    }
  }
});

grr.Renderer('FrontPage', {
  Layout: function(state) {
    // Update main's state from the hash
    if (grr.hash.main) {
      $.extend(grr.state, grr.hash);
      grr.layout(grr.hash.main, 'main');
    } else {
      grr.layout('UserDashboard', 'main');
    }
  }
});