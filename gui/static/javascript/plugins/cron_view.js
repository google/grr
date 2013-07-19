var grr = window.grr || {};

grr.Renderer('ManageCron', {
  Layout: function(state) {
    var bottomPaneId = state['id'] + '_bottomPane';

    grr.subscribe('cron_select', function(cronUrn) {
      grr.layout('CronJobManagementTabs', bottomPaneId,
                 {cron_job_urn: cronUrn});
    }, bottomPaneId);
  }
});

grr.Renderer('CronTable', {
  Layout: function(state) {
    //Receive the selection event and emit the detail.
    grr.subscribe('select_table_' + state['id'], function(node) {
      if (node) {
        var cronUrn = $(node).find('span[aff4_path]').attr('aff4_path');
        grr.publish('cron_select', cronUrn);
      }
    }, state['unique']);

    var selectedCronJobUrn;
    grr.subscribe('cron_select', function(cronJobUrn) {
      selectedCronJobUrn = cronJobUrn;

      var row = $("span[aff4_path='" + cronJobUrn + "']",
                  $('#' + state['unique'])).closest('tr');
      $('.cron-job-state-icon', row).each(function() {
        var cronJobState = $(this).attr('state');
        if (cronJobState == 'enabled') {
          $('#enable_cron_job_' + state['unique']).attr('disabled', 'true');
          $('#delete_cron_job_' + state['unique']).removeAttr('disabled');
          $('#disable_cron_job_' + state['unique']).removeAttr('disabled');
        } else if (cronJobState == 'disabled') {
          $('#enable_cron_job_' + state['unique']).removeAttr('disabled');
          $('#delete_cron_job_' + state['unique']).removeAttr('disabled');
          $('#disable_cron_job_' + state['unique']).attr('disabled', 'true');
        }
      });
    }, state['unique']);


    $('#enable_cron_job_dialog_' + state['unique']).on('show', function() {
      grr.layout('EnableCronJobConfirmationDialog',
                 'enable_cron_job_dialog_' + state['unique'],
                 {cron_job_urn: selectedCronJobUrn});
    }).on('hidden', function() {
      $('#' + state['unique']).trigger('refresh');
      $(this).html('');
    });

    $('#disable_cron_job_dialog_' + state['unique']).on('show', function() {
      grr.layout('DisableCronJobConfirmationDialog',
                 'disable_cron_job_dialog_' + state['unique'],
                 {cron_job_urn: selectedCronJobUrn});
    }).on('hidden', function() {
      $('#' + state['unique']).trigger('refresh');
      $(this).html('');
    });

    $('#delete_cron_job_dialog_' + state['unique']).on('show', function() {
      grr.layout('DeleteCronJobConfirmationDialog',
                 'delete_cron_job_dialog_' + state['unique'],
                 {cron_job_urn: selectedCronJobUrn});
    }).on('hidden', function() {
      $('#' + state['unique']).trigger('refresh');
      $(this).html('');
    });

    $('#schedule_hunt_cron_job_dialog_' + state['unique']).on(
        'shown', function() {
          grr.layout('ScheduleHuntCronJobDialog',
                     'schedule_hunt_cron_job_dialog_' + state['unique']);
        }).on('hidden', function() {
          $('#' + state['unique']).trigger('refresh');
          $(this).html('');
        });

    if (grr.hash.cron_job_urn) {
      $('#' + state['unique']).find("td:contains('" +
        grr.hash.cron_job_urn.split('/').reverse()[0] +
        "')").click();
    }
  }
});

grr.Renderer('CronJobView', {
  Layout: function(state) {
    var detailsPanel = $('#FlowDetails_' + state['unique']);
    var detailsPanelClose = $('#FlowDetailsClose_' + state['unique']);

    detailsPanelClose.click(function() {
      detailsPanel.addClass('hide');
    });

    grr.subscribe('flow_table_select', function(flow_id) {
      var selectedRow =
          $('#CronJobView_' + state['unique'] + ' tr.row_selected');
      detailsPanel.css('top', selectedRow.position().top + 'px');
      detailsPanel.removeClass('hide');

      grr.layout('ShowFlowInformation', 'FlowDetailsContent_' + state['unique'],
                 {flow: flow_id});
    }, state['unique']);
  }
});

grr.Renderer('ScheduleHuntCronJobDialog', {
  Layout: function(state) {
    $('#Wizard_' + state['unique']).data({
      hunt_periodicity: 7,
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

grr.Renderer('CronHuntConfigureSchedule', {
  Layout: function(state) {
    var containerId = '#CronHuntConfigureSchedule_' + state['unique'];
    var wizardState = $(containerId).closest('.Wizard').data();

    $('select[name=periodicity]', $(containerId)).change(function() {
      wizardState['hunt_periodicity'] = parseInt($(this).val());
    }).each(function() {
      $(this).val(wizardState['hunt_periodicity']);
    });
  }
});
