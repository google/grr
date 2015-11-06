var grr = window.grr || {};

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
