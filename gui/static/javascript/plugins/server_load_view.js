var grr = window.grr || {};

grr.Renderer('ScalarGraphRenderer', {
  Layout: function(state) {
    var unique = state.unique;
    var graph = state.graph;

    var data = [];
    for (var serieName in graph.series) {
      var serie = graph.series[serieName];
      data.push({label: serie.title,
                 data: serie.data});
    }

    var config = {
      xaxis: {
        mode: 'time',
        axisLabel: 'Time'
      },
      yaxis: {
        axisLabel: graph.yAxisLabel
      }
    };
    $.plot('#' + graph.name + '_' + unique,
           data, config);
  }
});

grr.Renderer('ServerLoadView', {
  Layout: function(state) {
    var unique = state.unique;
    var id = state.id;
    var renderer = state.renderer;
    var graphs = state.graphs;

    $('#durations_' + unique + ' button').click(function() {
      grr.layout(renderer, id, {
        duration: $(this).attr('name')
      });
    });
  }
});
