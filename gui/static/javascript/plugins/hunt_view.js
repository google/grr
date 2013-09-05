var grr = window.grr || {};

grr.Renderer('HuntTable', {
  Layout: function(state) {
    var unique = state.unique;
    var id = state.id;

    // We use this dom node to communicate between the different callbacks.
    var dom_node = $('#' + id);

    $('#new_hunt_dialog_' + unique).on('shown', function(event) {
      if (event.target != this) {
        return;
      }

      grr.layout('NewHunt', 'new_hunt_dialog_' + unique);
    }).on('hidden', function(event) {
      if (event.target != this) return;

      $('#' + unique).trigger('refresh');
      $(this).html('');
    });

    $('#run_hunt_dialog_' + unique).on('show', function() {
      grr.layout('RunHuntConfirmationDialog',
                 'run_hunt_dialog_' + unique, dom_node.data());
    }).on('hidden', function() {
      $('#' + unique).trigger('refresh');
      $(this).html('');
    });

    $('#pause_hunt_dialog_' + unique).on('show', function() {
      grr.layout('PauseHuntConfirmationDialog',
                 'pause_hunt_dialog_' + unique, dom_node.data());
    }).on('hidden', function() {
      $('#' + unique).trigger('refresh');
      $(this).html('');
    });

    $('#modify_hunt_dialog_' + unique).on('show', function() {
      grr.layout('ModifyHuntDialog', 'modify_hunt_dialog_' + unique,
                 dom_node.data());
    }).on('hidden', function() {
      $('#' + unique).trigger('refresh');
      $(this).html('');
    });

    grr.subscribe('WizardComplete', function(wizardStateName) {
      $('#new_hunt_dialog_' + unique).modal('hide');
    }, 'new_hunt_dialog_' + unique);

    grr.subscribe('file_select', function(hunt_id) {
      dom_node.data('hunt_id', hunt_id);
      grr.hash.hunt_id = hunt_id;

      var row = $('span[aff4_path="' + hunt_id + '"]', '#' + id).closest('tr');
      $('.hunt-state-icon', row).each(function() {
        var state = $(this).attr('state');
        if (state == 'STARTED') {
          // Hunt is currently running - we can not modify it until its stopped.
          $('#run_hunt_' + unique).attr('disabled', 'true');
          $('#modify_hunt_' + unique).attr('disabled', 'true');
          $('#pause_hunt_' + unique).removeAttr('disabled');

          // Hunt is paused, can be run again.
        } else if (state == 'PAUSED' || state == 'STOPPED') {
          $('#run_hunt_' + unique).removeAttr('disabled');
          $('#modify_hunt_' + unique).removeAttr('disabled');
          $('#pause_hunt_' + unique).attr('disabled', 'true');
        }
      });
    }, 'run_hunt_' + unique);

  }
});
