var grr = window.grr || {};

grr.Renderer('NotificationBar', {
  Layout: function(state) {
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
    $('#user_settings_dialog').detach().appendTo('body');

    $('#notification_dialog').on('show.bs.modal', function() {
      grr.layout('ViewNotifications', 'notification_dialog_body');
      grr.publish('NotificationCount', 0);
    });

    $('#user_settings_dialog').on('show.bs.modal', function() {
      grr.layout('UserSettingsDialog', 'user_settings_dialog');
    }).on('hidden.bs.modal', function() {
      $(this).html('');
    });
  }
});


grr.Renderer('UserSettingsDialog', {
  RenderAjax: function(state) {
    document.location.reload(true);
  }
});


grr.Renderer('ViewNotifications', {
  Layout: function(state) {
    //Receive the selection event and emit a path
    grr.subscribe('select_table_' + state['id'], function(node) {
      if (node) {
        var element = node.find('a');
        if (element) {
          if (element.attr('notification_type') == 'DownloadFile') {
            var parsedHash = grr.parseHashState(element.attr('target_hash'));
            var fileState = { aff4_path: parsedHash['aff4_path']};
            grr.downloadHandler(element, fileState, false,
                                '/render/Download/DownloadView');
            element.trigger('download');
          } else {
            grr.loadFromHash(element.attr('target_hash'));
          }
        }
      }
    }, state['unique']);
  }
});
