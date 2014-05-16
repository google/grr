var grr = window.grr || {};

grr.Renderer('ManageCron', {
  Layout: function(state) {
    var bottomPaneId = state['id'] + '_bottomPane';

    grr.subscribe('cron_select', function(cronUrn) {
      grr.layout('CronJobManagementTabs', bottomPaneId,
                 {cron_job_urn: cronUrn});
    }, state['unique']);
  }
});

grr.Renderer('CronTable', {
  Layout: function(state) {
    var unique = state.unique;
    var id = state.id;

    // We use this dom node to communicate between the different callbacks.
    var dom_node = $('#' + id);

    //Receive the selection event and emit the detail.
    grr.subscribe('select_table_' + id, function(node) {
      if (node) {
        var cronUrn = $(node).find('span[aff4_path]').attr('aff4_path');
        grr.publish('cron_select', cronUrn);
      }
    }, unique);

    grr.subscribe('cron_select', function(cron_urn) {
      dom_node.data('cron_urn', cron_urn);
      grr.hash.cron_urn = cron_urn;

      var row = $("span[aff4_path='" + cron_urn + "']",
          '#' + unique).closest('tr');

      $('.cron-job-state-icon', row).each(function() {
        var state = $(this).attr('state');
        $('#run_cron_job_' + unique).removeAttr('disabled');
        $('#delete_cron_job_' + unique).removeAttr('disabled');

        if (state == 'enabled') {
          $('#enable_cron_job_' + unique).attr('disabled', 'true');
          $('#disable_cron_job_' + unique).removeAttr('disabled');
        } else if (state == 'disabled') {
          $('#enable_cron_job_' + unique).removeAttr('disabled');
          $('#disable_cron_job_' + unique).attr('disabled', 'true');
        }
      });
    }, unique);


    $('#enable_cron_job_dialog_' + unique).on('show', function(event) {
      if (event.target != this) return;

      grr.layout('EnableCronJobConfirmationDialog',
                 'enable_cron_job_dialog_' + unique, dom_node.data());
    }).on('hidden', function(event) {
      $('#' + unique).trigger('refresh');
      $(this).html('');
    });

    $('#run_cron_job_dialog_' + unique).on('show', function(event) {
      if (event.target != this) return;

      grr.layout('ForceRunCronJobConfirmationDialog',
                 'run_cron_job_dialog_' + unique, dom_node.data());
    }).on('hidden', function(event) {
      $('#' + unique).trigger('refresh');
      $(this).html('');
    });


    $('#disable_cron_job_dialog_' + unique).on('show', function(event) {
      if (event.target != this) return;

      grr.layout('DisableCronJobConfirmationDialog',
                 'disable_cron_job_dialog_' + unique, dom_node.data());

    }).on('hidden', function(event) {
      if (event.target != this) return;

      $('#' + unique).trigger('refresh');
      $(this).html('');
    });

    $('#delete_cron_job_dialog_' + unique).on('show', function(event) {
      if (event.target != this) return;

      grr.layout('DeleteCronJobConfirmationDialog',
                 'delete_cron_job_dialog_' + unique, dom_node.data());

    }).on('hidden', function(event) {
      if (event.target != this) return;

      $('#' + unique).trigger('refresh');
      $(this).html('');
    });

    $('#schedule_hunt_cron_job_dialog_' + unique).on(
        'shown', function(event) {
          if (event.target != this) return;

          grr.layout('ScheduleHuntCronJobDialog',
                     'schedule_hunt_cron_job_dialog_' + unique);

        }).on('hidden', function(event) {
          if (event.target != this) return;

          $('#' + unique).trigger('refresh');
          $(this).html('');
        });

    if (grr.hash.cron_job_urn) {
      $('#' + unique).find("td:contains('" +
          grr.hash.cron_job_urn.split('/').reverse()[0] +
              "')").click();
    }
  }
});

grr.Renderer('CronConfigureFlow', {
  Layout: function(state) {
    var id = state.id;
    var unique = state.unique;

    grr.subscribe('flow_select', function(path) {
      var pane_id = id + '_rightPane';

      // Record the flow in the form data.
      $('#' + pane_id).closest('.FormData').data('flow_path', path);
      grr.layout('CronFlowForm', pane_id, { flow_path: path });

    }, unique);
  }
});

grr.Renderer('CronJobView', {
  Layout: function(state) {
    var unique = state.unique;
    var detailsPanel = $('#FlowDetails_' + unique);
    var detailsPanelClose = $('#FlowDetailsClose_' + unique);

    detailsPanelClose.click(function() {
      detailsPanel.addClass('hide');
    });

    grr.subscribe('flow_table_select', function(flow_id) {
      var selectedRow =
          $('#CronJobView_' + unique + ' tr.row_selected');
      detailsPanel.css('top', selectedRow.position().top + 'px');
      detailsPanel.removeClass('hide');

      grr.layout('ShowFlowInformation', 'FlowDetailsContent_' + unique,
                 {flow: flow_id});
    }, unique);
  }
});


grr.Renderer('ScheduleHuntCronJobDialog', {
  Layout: function(state) {
  }
});

grr.Renderer('CronHuntConfigureSchedule', {
  Layout: function(state) {
  }
});
