var grr = window.grr || {};

grr.Renderer('ContainerFileTable', {
  Layout: function(state) {
    var id = state.id;
    var unique = state.unique;
    var renderer = state.renderer;
    var container = state.container;

    //Receive the selection event and emit a path
    grr.subscribe('select_table_' + id, function(node) {
      if (node) {
        var element = node.find('span[aff4_path]');
        if (element) {
          grr.publish('file_select', element.attr('aff4_path'));
        }
      }
    }, unique);

    // Redraw the table if the query changes
    grr.subscribe('query_changed', function(query) {
      grr.layout(renderer, id, {
        container: container,
        query: query
      });
    }, unique);
  }
});

grr.Renderer('ContainerToolbar', {
  Layout: function(state) {
    var unique = state.unique;

    $('#export').button().click(function() {
      $('input#csrfmiddlewaretoken').val(grr.getCookie('csrftoken'));
      $('input#csv_query').val($('input#query').val());
      $('input#csv_reason').val(grr.state.reason);
      $('#csv_' + unique).submit();
    });

    grr.subscribe('tree_select', function(path) {
      $('input#query').val("subject startswith '" +
          path.replace("'", "\\'") + "/'");
      $('#form_' + unique).submit();
    }, 'form_' + unique);

    $('#form_' + unique).submit(function() {
      query = $('input#query').val();
      grr.publish('query_changed', query);
      return false;
    });
  }
});


grr.Renderer('ContainerViewer', {
  Layout: function(state) {
    var unique = state.unique;
    var id = state.id;

    grr.state.container = grr.hash.container;
    grr.state.query = grr.hash.query || '';

    grr.layout('ContainerToolbar', 'toolbar_' + id);
    grr.layout('ContainerViewerSplitter', unique);
  }
});
