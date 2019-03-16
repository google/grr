/*global Gallery,Dygraph,data */
Gallery.register(
  'linear-regression',
  {
    name: 'Linear Regressions',
    title: 'Linear Regression Demo',
    setup: function(parent) {
      parent.innerHTML = [
        "<p>Click the buttons to generate linear regressions over either data ",
        "series. If you zoom in and then click the regression button, the regression ",
        "will only be run over visible points. Zoom back out to see what the local ",
        "regression looks like over the full data.</p> ",
        "<div id='demodiv' style='width: 480px; height: 320px;'></div>",
        "<div style='text-align:center; width: 480px'>",
        "<button style='color: green;' id='ry1'>Regression (Y1)</button> ",
        "<button style='color: blue;' id='ry2'>Regression (Y2)</button> ",
        "<button id='clear'>Clear Lines</button>",
        "</div>"].join("\n");
    },
    run: function() {
      var g, regression, clearLines;  // defined below
      document.getElementById("ry1").onclick = function() { regression(1); };
      document.getElementById("ry2").onclick = function() { regression(2); };
      document.getElementById("clear").onclick = function() { clearLines(); };

      var data = [];
      for (var i = 0; i < 120; i++) {
        data.push([i,
                   i / 5.0 + 10.0 * Math.sin(i / 3.0),
                   30.0 - i / 5.0 - 10.0 * Math.sin(i / 3.0 + 1.0)]);
      }

      // coefficients of regression for each series.
      // if coeffs = [ null, [1, 2], null ] then we draw a regression for series 1
      // only. The regression line is y = 1 + 2 * x.
      var coeffs = [ null, null, null ];
      regression = function(series) {
        // Only run the regression over visible points.
        var range = g.xAxisRange();

        var sum_xy = 0.0, sum_x = 0.0, sum_y = 0.0, sum_x2 = 0.0, num = 0;
        for (var i = 0; i < g.numRows(); i++) {
          var x = g.getValue(i, 0);
          if (x < range[0] || x > range[1]) continue;

          var y = g.getValue(i, series);
          if (y === null || y === undefined) continue;
          if (y.length == 2) {
            // using fractions
            y = y[0] / y[1];
          }

          num++;
          sum_x += x;
          sum_y += y;
          sum_xy += x * y;
          sum_x2 += x * x;
        }

        var a = (sum_xy - sum_x * sum_y / num) / (sum_x2 - sum_x * sum_x / num);
        var b = (sum_y - a * sum_x) / num;

        coeffs[series] = [b, a];
        if (typeof(console) != 'undefined') {
          console.log("coeffs(" + series + "): [" + b + ", " + a + "]");
        }

        g.updateOptions({});  // forces a redraw.
      };

      clearLines = function() {
        for (var i = 0; i < coeffs.length; i++) coeffs[i] = null;
        g.updateOptions({});
      };

      function drawLines(ctx, area, layout) {
        if (typeof(g) == 'undefined') return;  // won't be set on the initial draw.

        var range = g.xAxisRange();
        for (var i = 0; i < coeffs.length; i++) {
          if (!coeffs[i]) continue;
          var a = coeffs[i][1];
          var b = coeffs[i][0];

          var x1 = range[0];
          var y1 = a * x1 + b;
          var x2 = range[1];
          var y2 = a * x2 + b;

          var p1 = g.toDomCoords(x1, y1);
          var p2 = g.toDomCoords(x2, y2);

          var c = Dygraph.toRGB_(g.getColors()[i - 1]);
          c.r = Math.floor(255 - 0.5 * (255 - c.r));
          c.g = Math.floor(255 - 0.5 * (255 - c.g));
          c.b = Math.floor(255 - 0.5 * (255 - c.b));
          var color = 'rgb(' + c.r + ',' + c.g + ',' + c.b + ')';
          ctx.save();
          ctx.strokeStyle = color;
          ctx.lineWidth = 1.0;
          ctx.beginPath();
          ctx.moveTo(p1[0], p1[1]);
          ctx.lineTo(p2[0], p2[1]);
          ctx.closePath();
          ctx.stroke();
          ctx.restore();
        }
      }

      g = new Dygraph(
              document.getElementById("demodiv"),
              data,
              {
                labels: ['X', 'Y1', 'Y2'],
                underlayCallback: drawLines,
                drawPoints: true,
                drawAxesAtZero: true,
                strokeWidth: 0.0
              }
          );
    }
  });
