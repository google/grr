var grr = window.grr || {};

grr.Renderer('NotificationBar', {
  Layout: function() {
    grr.subscribe('NotificationCount', function(number) {
      var button;

      if (parseInt(number) > 0) {
        button = $('#notification_button').removeClass('btn-info');
        button = $('#notification_button').addClass('btn-danger');
      } else {
        button = $('#notification_button').addClass('btn-info');
        button = $('#notification_button').removeClass('btn-danger');
      }
      button.text(number);
    }, 'notification_button');

    grr.poll('NotificationCount', 'notification_button', function(data) {
      if (data) {
        grr.publish('NotificationCount', data.number);
      }

      return true;
    }, 60000, grr.state, 'json');

    $('#notification_dialog').detach().appendTo('body');
    $('#notification_dialog').on('show', function() {
      grr.layout('ViewNotifications', 'notification_dialog_body');
      grr.publish('NotificationCount', 0);
    });
  }
});

grr.Renderer('ViewNotifications', {
  Layout: function(state) {
    //Receive the selection event and emit a path
    grr.subscribe('select_table_' + state['id'], function(node) {
      if (node) {
        var element = node.find('a');
        if (element) {
          grr.loadFromHash(element.attr('target_hash'));
        }
      }
    }, state['unique']);
  }
});
