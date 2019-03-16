/*global Gallery,Dygraph,data */
Gallery.register(
  'highlighted-region',
  {
    name: 'Highlighted Region',
    title: 'Draws a time series with an unusual region highlighted',
    setup: function(parent) {
      parent.innerHTML = [
        "<div id='div_g' style='width:600px; height:300px;'></div>",
        "<p>When you zoom and pan, the region remains highlighted.</p>"].join("\n");
    },
    run: function() {
      // A basic sinusoidal data series.
      var data = [];
      for (var i = 0; i < 1000; i++) {
        var base = 10 * Math.sin(i / 90.0);
        data.push([i, base, base + Math.sin(i / 2.0)]);
      }

      // Shift one portion out of line.
      var highlight_start = 450;
      var highlight_end = 500;
      for (var i = highlight_start; i <= highlight_end; i++) {
        data[i][2] += 5.0;
      }

      new Dygraph(
          document.getElementById("div_g"),
          data,
          {
            labels: ['X', 'Est.', 'Actual'],
            animatedZooms: true,
            underlayCallback: function(canvas, area, g) {
              var bottom_left = g.toDomCoords(highlight_start, -20);
              var top_right = g.toDomCoords(highlight_end, +20);

              var left = bottom_left[0];
              var right = top_right[0];

              canvas.fillStyle = "rgba(255, 255, 102, 1.0)";
              canvas.fillRect(left, area.y, right - left, area.h);
            }

          }
      );
    }
  });
