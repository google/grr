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
