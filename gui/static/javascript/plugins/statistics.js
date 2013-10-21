/**
 * @fileoverview Rendering javascript for statistics.py.
 */

var grr = window.grr || {};

grr.Renderer('PieChart', {
  Layout: function(state) {
    var unique = state.unique;
    $('#graph_' + unique).resize(function() {
      $('#graph_' + unique).html('');
      $.plot($('#graph_' + unique), state.data, {
        series: {
          pie: {
            show: true,
            label: {
              show: true,
              radius: 0.5,
              formatter: function(label, series) {
                return ('<div style="font-size:8pt;' +
                        'text-align:center;padding:2px;color:white;">' +
                        label + '<br/>' + Math.round(series.percent) +
                        '%</div>');
              },
              background: { opacity: 0.8 }
            }
          }
        },
        grid: {
          hoverable: true,
          clickable: true
        }
      });
    });

    $('#graph_' + unique).bind('plothover', function(event, pos, obj) {
      if (obj) {
        percent = parseFloat(obj.series.percent).toFixed(2);
        $('#hover_' + unique).html('<span style="font-weight: bold; color: ' +
                        obj.series.color + '">' + obj.series.label + ' ' +
                        obj.series.data[0][1] + ' (' + percent + '%)</span>');
      }
    });

    $('#graph_' + unique).resize();
  }
});

grr.Renderer('LastActiveReport', {
  Layout: function(state) {
    var unique = state.unique;
    var options = {
      xaxis: {mode: 'time',
              timeformat: '%y/%m/%d'},
      lines: {show: true},
      points: {show: true},
      zoom: {interactive: true},
      pan: {interactive: true},
      grid: {clickable: true, autohighlight: true}
    };

    var placeholder = $('#' + unique);
    var plot = $.plot(placeholder, state.graphs, options);

    placeholder.bind('plotclick', function(event, pos, item) {
      if (item) {
        var date = new Date(item.datapoint[0]);
        $('#' + unique + '_click').text('On ' + date.toDateString() +
          ', there were ' + item.datapoint[1] + ' ' + item.series.label +
          ' systems.');
      }
    });
  }
});

grr.Renderer('CustomXAxisChart', {
  Layout: function(state) {
    var unique = state.unique;
    $.plot($('#graph_' + unique), state.data, {
      series: {
        bars: {
          show: true,
          barWidth: 0.2
        },
        background: { opacity: 0.8 }
      },
      xaxis: {
        min: 0,
        ticks: state.xaxis_ticks
      },
      grid: {
        hoverable: true,
        clickable: true
      }
    });

    $('#graph_' + unique).bind('plothover', function(event, pos, obj) {
      if (obj) {
        $('#hover_' + unique).html(
          '<span style="font-weight: bold; color: ' +
          obj.series.color + '"> <b>' +
          state.xaxis_ticks[obj.seriesIndex][1] +
          ': ' + obj.datapoint[1] + '</b>' + '</span>');
      }
    });
  }
});

