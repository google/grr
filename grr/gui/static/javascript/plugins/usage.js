var grr = window.grr || {};

grr.Renderer('StackChart', {
  Layout: function(state) {
    var unique = state.unique;
    var specs = state.specs;

    $('#' + unique).resize(function() {
      $('#' + unique).html('');
      $.plot($('#' + unique), specs, {
        series: {
          stack: true,
          bars: {
            show: true,
            barWidth: 0.6
          },
          label: {
            show: true,
            radius: 0.5
          },
          background: { opacity: 0.8 }
        },
        grid: {
          hoverable: true,
          clickable: true
        }
      });
    });

    $('#' + unique).bind('plothover', function(event, pos, obj) {
      if (obj) {
        grr.test_obj = obj;
        $('#hover').html(
            '<span style="font-weight: bold; color: ' +
                obj.series.color + '"> <b>' + obj.series.label + '</b>: ' +
                (obj.datapoint[1] - obj.datapoint[2]) + '</span>');
      }
    });

    $('#' + unique).resize();
  }
});
