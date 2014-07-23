var grr = window.grr || {};

grr.Renderer('RequestTable', {
  Layout: function(state) {
    var unique = state.unique;
    var id = state.id;

    //Receive the selection event and emit a path
    grr.subscribe('select_table_' + id, function(node) {
      if (node) {
        var task_id = node.find('span[rdfvalue]').attr('rdfvalue');
        grr.publish('request_table_select', task_id);
      }
    }, unique);
  }
});

grr.Renderer('RequestTabs', {
  Layout: function(state) {
    var unique = state.unique;

    grr.subscribe('request_table_select', function(task_id) {
      $('#' + unique).data().state.task_id = task_id;
      $('#' + unique + ' li.active a').click();
    }, unique);
  }
});

grr.Renderer('ClientLoadView', {
  Layout: function(state) {
    var unique = state.unique;
    var user_cpu_data = state.user_cpu_data;
    var system_cpu_data = state.system_cpu_data;
    var read_bytes_data = state.read_bytes_data;
    var write_bytes_data = state.write_bytes_data;
    var read_count_data = state.read_count_data;
    var write_count_data = state.write_count_data;

    var detailsPanel = $('#FlowDetails_' + unique);
    var detailsPanelClose = $('#FlowDetailsClose_' + unique);

    detailsPanelClose.click(function() {
      detailsPanel.addClass('hide');
    });

    $('#' + unique + ' a.flow_details_link').click(function(event) {
      var flowUrn = $(this).attr('flow_urn');

      detailsPanel.css('top', $(this).position().top + 'px');
      detailsPanel.removeClass('hide');
      grr.layout('ShowFlowInformation', 'FlowDetailsContent_' + unique,
                 {flow: flowUrn});
      event.preventDefault();
    });

    $.plot('#client_cpu_' + unique,
           [{
             label: 'User',
             data: user_cpu_data
           },
            {
              label: 'System',
              data: system_cpu_data
            }],
           {
             xaxis: {
               mode: 'time',
               axisLabel: 'Time'
             },
             yaxis: {
               axisLabel: 'CPU load'
             }
           });

    $.plot('#client_io_bytes_' + unique,
           [{
             label: 'Read',
             data: read_bytes_data
           },
            {
              label: 'Write',
              data: write_bytes_data
            }],
           {
             xaxis: {
               mode: 'time',
               axisLabel: 'Time'
             },
             yaxis: {
               axisLabel: 'Bytes'
             }
           });

    $.plot('#client_io_count_' + unique,
           [{
             label: 'Read',
             data: read_count_data
           },
            {
              label: 'Write',
              data: write_count_data
            }],
           {
             xaxis: {
               mode: 'time',
               axisLabel: 'Time'
             },
             yaxis: {
               axisLabel: 'Number of operations'
             }
           });
  }
});
