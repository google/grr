var grr = window.grr || {};

grr.Renderer('TimelineMain', {
  Layout: function(state) {
    var unique = state.unique;
    var id = state.id;

    var query_state = {
      container: grr.hash.container,
      query: grr.hash.query || ''
    };

    grr.layout('TimelineToolbar', 'toolbar_' + id, query_state);
    grr.layout('TimelineViewerSplitter', unique, query_state);
  }
});

grr.Renderer('TimelineToolbar', {
  Layout: function(state) {
    var unique = state.unique;
    var container = state.container;
    var reason = state.reason;

    var query_state = {query: $('input#container_query').val(),
                       container: container,
                       reason: reason,
                       client_id: grr.state.client_id
                      };
    grr.downloadHandler($('#export_' + unique), state, true,
                        '/render/Download/EventTable');

    $('#form_' + unique).submit(function() {
      var query = $('input#container_query').val();
      grr.publish('query_changed', query);
      grr.publish('hash_state', 'query', query);
      return false;
    });
  }
});

grr.Renderer('EventTable', {
  Layout: function(state) {
    var unique = state.unique;
    var id = state.id;
    var container = state.container;
    var renderer = state.renderer;

    grr.subscribe('query_changed', function(query) {
      grr.layout(renderer, id, {
        container: container,
        query: query
      });
    }, unique);

    grr.subscribe('select_table_' + id, function(node) {
      var event_id = node.find('td').first().text();

      grr.publish('event_select', event_id);
    }, unique);
  }
});

grr.Renderer('EventViewTabs', {
  Layout: function(state) {
    var unique = state.unique;
    var id = state.id;
    var event_queue = state.event_queue;
    var container = state.container;
    var renderer = state.renderer;

    // Listen to the event change events and switch to the first tab.
    grr.subscribe(event_queue, function(event) {
      grr.publish('hash_state', 'event', event);
      grr.layout(renderer, id, {
        event: event,
        container: container
      });
    }, 'tab_contents_' + unique);
  }
});
