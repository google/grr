var grr = window.grr || {};

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

    //Receive the selection event and emit a client_id
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
  }
});

grr.Renderer('SearchHostView', {
  Layout: function(state) {
    $('#search_host').submit(function() {
      var input = $('input[name="q"]').val();
      var sha_regex = /^[A-F0-9]{64}$/i;

      if (sha_regex.test(input)) {
        grr.layout('FilestoreTable', 'main', {q: input});
      } else {
        grr.layout('HostTable', 'main', {q: input});
      }

      return false;
    }).find('input[name=q]').focus();
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
