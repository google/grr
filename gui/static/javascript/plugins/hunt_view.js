var grr = window.grr || {};

grr.Renderer('ManageHunts', {
  Layout: function(state) {
    // If hunt_id in hash, click that row.
    if (grr.hash.hunt_id) {
      var basename = grr.hash.hunt_id.split('/').reverse()[0];
      $("table.HuntTable td:contains('" + basename + "')").click();
    }
  }
});

grr.Renderer('HuntViewTabs', {
  Layout: function(state) {
    var unique = state.unique;

    // When the hunt id is selected, redraw the tabs below.
    grr.subscribe('file_select', function(hunt_id) {
      grr.layout('HuntViewTabs', 'main_bottomPane', {hunt_id: hunt_id});
    }, unique);
  }
});

grr.Renderer('HuntClientTableRenderer', {
  Layout: function(state) {
    var unique = state.unique;
    var hunt_hash = state.hunt_hash;

    if (!grr.state.hunt_id) {
      // Refresh the page with the hunt_id from the hash.
      grr.state.hunt_id = grr.hash.hunt_id;
      grr.layout('ContentView', 'content', grr.state);
    }

    // Add click handler to the backlink.
    $('#backlink_' + unique).click(function() {
      // clean up our state before we jump back to the hunt.
      delete grr.state.client_id;
      grr.loadFromHash(hunt_hash);
    });

    $('#' + unique + '_select').change(function() {
      grr.state.completion_status = $('#' + unique + '_select').val();
      grr.layout('HuntClientTableRenderer', 'main_topPane', grr.state);
    });
  }
});

grr.Renderer('HuntOverviewRenderer', {
  RenderAjax: function(state) {
    var unique = state.unique;
    var subject = state.subject;
    var hunt_id = state.hunt_id;

    // We execute CheckAccess renderer with silent=true. Therefore it searches
    // for an approval and sets correct reason if approval is found. When
    // CheckAccess completes, we execute HuntViewRunHunt renderer, which
    // tries to run an actual hunt. If the approval wasn't found on CheckAccess
    // stage, it will fail due to unauthorized access and proper ACLDialog will
    // be displayed.
    grr.layout('CheckAccess', 'RunHuntResult_' + unique,
               {silent: true, subject: subject},
               function() {
                 grr.layout('HuntViewRunHunt', 'RunHuntResult_' + unique,
                            { hunt_id: hunt_id });
               });
  }
});

grr.Renderer('HuntClientViewTabs', {
  Layout: function(state) {
    var unique = state.unique;
    var hunt_id = state.hunt_id;

    // When the hunt id is selected, redraw the tabs below.
    grr.subscribe('file_select', function(client_id) {
      grr.layout('HuntClientViewTabs', 'main_bottomPane', {
        hunt_client: client_id,
        hunt_id: hunt_id
      });
    }, unique);
  }
});

grr.Renderer('HuntClientGraphRenderer', {
  Layout: function(state) {
    var unique = state.unique;
    var hunt_id = state.hunt_id;

    var button = $('#' + unique).button();
    var handlerState = {hunt_id: hunt_id};
    grr.downloadHandler(button, handlerState, false,
                        '/render/Download/HuntClientCompletionGraphRenderer');
  }
});

grr.Renderer('HuntStatsRenderer', {
  Layout: function(state) {
    var unique = state.unique;
    var user_cpu_json_data = state.user_cpu_json_data;
    var system_cpu_json_data = state.system_cpu_json_data;
    var network_bytes_sent_json_data = state.network_bytes_sent_json_data;

    $('#performers_' + unique + " a[client_id!='']").click(function() {
      client_id = $(this).attr('client_id');
      grr.state.client_id = client_id;
      grr.publish('hash_state', 'c', client_id);

      // Clear the authorization for new clients.
      grr.publish('hash_state', 'reason', '');
      grr.state.reason = '';

      grr.publish('hash_state', 'main', null);
      grr.publish('client_selection', client_id);
    });

    function formatTimeTick(tick) {
      if (Math.abs(Math.floor(tick) - tick) > 1e-7) {
        return tick.toFixed(1);
      } else {
        return Math.floor(tick);
      }
    }

    function formatBytesTick(tick) {
      if (tick < 1024) {
        return tick + 'B';
      } else {
        return Math.round(tick / 1024) + 'K';
      }
    }

    function plotStats(statName, jsonString, formatTickFn) {
      var srcData = $.parseJSON(jsonString);
      var data = [];
      var ticks = [];
      for (var i = 0; i < srcData.length; ++i) {
        data.push([i, srcData[i][1]]);
        ticks.push([i + 0.5, formatTickFn(srcData[i][0])]);
      }

      $.plot('#' + statName + '_' + unique, [data], {
        series: {
          bars: {
            show: true,
            lineWidth: 1
          }
        },
        xaxis: {
          tickLength: 0,
          ticks: ticks
        },
        yaxis: {
          minTickSize: 1,
          tickDecimals: 0
        }
      });
    }

    plotStats('user_cpu',
              user_cpu_json_data, formatTimeTick);
    plotStats('system_cpu',
              system_cpu_json_data, formatTimeTick);
    plotStats('network_bytes_sent',
              network_bytes_sent_json_data, formatBytesTick);
  }
});

grr.Renderer('HuntTable', {
  Layout: function(state) {
    var unique = state.unique;
    var id = state.id;

    // We use this dom node to communicate between the different callbacks.
    var dom_node = $('#' + id);

    $('#new_hunt_dialog_' + unique).on('shown.bs.modal', function(event) {
      if (event.target != this) {
        return;
      }

      grr.layout('NewHunt', 'new_hunt_dialog_' + unique);
    }).on('hidden.bs.modal', function(event) {
      if (event.target != this) return;

      $('#' + unique).trigger('refresh');
      $(this).html('');
    });

    $('#run_hunt_dialog_' + unique).on('show.bs.modal', function() {
      grr.layout('RunHuntConfirmationDialog',
                 'run_hunt_dialog_' + unique, dom_node.data());
    }).on('hidden.bs.modal', function() {
      $('#' + unique).trigger('refresh');
      $(this).html('');
    });

    $('#pause_hunt_dialog_' + unique).on('show.bs.modal', function() {
      grr.layout('PauseHuntConfirmationDialog',
                 'pause_hunt_dialog_' + unique, dom_node.data());
    }).on('hidden.bs.modal', function() {
      $('#' + unique).trigger('refresh');
      $(this).html('');
    });

    $('#modify_hunt_dialog_' + unique).on('show.bs.modal', function() {
      grr.layout('ModifyHuntDialog', 'modify_hunt_dialog_' + unique,
                 dom_node.data());
    }).on('hidden.bs.modal', function() {
      $('#' + unique).trigger('refresh');
      $(this).html('');
    });

    $('#toggle_robot_hunt_display_' + unique).click(function() {
      $('#body_main_topPane tr').each(function() {
        if ($(this).hasClass('robot-hunt')) {
          $(this).toggleClass('hide');
        }
      });
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

grr.Renderer('HuntResultsRenderer', {
  Layout: function(state) {
    var unique = state.unique;
    var hunt_id = state.hunt_id;
    var exportable_results = state.exportable_results;

    if (exportable_results) {
      var tar_elements_selector = '#generate_archive_' + unique +
          ' *[name=generate_tar]';
      $(tar_elements_selector).click(function() {
        // We execute CheckAccess renderer with silent=true. Therefore it
        // searches for an approval and sets correct reason if approval is
        // found. When CheckAccess completes, we execute HuntGenerateResultsZip
        // renderer, which tries to run an actual hunt. If the approval
        // wasn't found on CheckAccess stage, it will fail due to unauthorized
        // access and proper ACLDialog will be displayed.
        grr.layout('CheckAccess', 'generate_action_' + unique,
                   {silent: true, subject: hunt_id},
                   function() {
                     grr.layout('HuntGenerateResultsArchive',
                                'generate_action_' + unique,
                                {hunt_id: hunt_id, format: 'TAR_GZIP'});
                   });

        $('#generate_archive_' + unique + ' button').attr(
            'disabled', 'disabled');
      });

      var zip_elememnts_selector = '#generate_archive_' + unique +
          ' *[name=generate_zip]';
      $(zip_elememnts_selector).click(function() {
        grr.layout('CheckAccess', 'generate_action_' + unique,
                   {silent: true, subject: hunt_id},
                   function() {
                     grr.layout('HuntGenerateResultsArchive',
                                'generate_action_' + unique,
                                {hunt_id: hunt_id, format: 'ZIP'});
                   });
        $('#generate_archive_' + unique + ' button').attr(
            'disabled', 'disabled');
      });

      if (navigator.appVersion.indexOf('Mac') != -1) {
        $('#generate_archive_' + unique + ' .export_zip').hide();
      } else {
        $('#generate_archive_' + unique + ' .export_tar').hide();
      }
    }
  }
});

grr.Renderer('CSVOutputPluginNoteRenderer', {
  Layout: function(state) {
    var unique = state.unique;

    $('#' + unique + '.csv-output-note a').each(function(index, element) {
      var fileState = { aff4_path: $(element).attr('aff4_path') };
      grr.downloadHandler($(element), fileState, false,
                          '/render/Download/DownloadView');
    }).click(function() {
      $(this).trigger('download');
    });
  }
});
