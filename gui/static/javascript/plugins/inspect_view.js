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
