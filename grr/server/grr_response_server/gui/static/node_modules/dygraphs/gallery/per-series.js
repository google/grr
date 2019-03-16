/*global Gallery,Dygraph,data */
Gallery.register(
  'per-series',
  {
    name: 'Per-series properties',
    title: 'Chart with per-series properties',
    setup: function(parent) {
      parent.innerHTML = "<div id='demodiv'>";
    },
    run: function() {
      new Dygraph(
              document.getElementById("demodiv"),
              function() {
                var zp = function(x) { if (x < 10) return "0"+x; else return x; };
                var r = "date,parabola,line,another line,sine wave\n";
                for (var i=1; i<=31; i++) {
                r += "200610" + zp(i);
                r += "," + 10*(i*(31-i));
                r += "," + 10*(8*i);
                r += "," + 10*(250 - 8*i);
                r += "," + 10*(125 + 125 * Math.sin(0.3*i));
                r += "\n";
                }
                return r;
              },
              {
                strokeWidth: 2,
                'parabola': {
                  strokeWidth: 0.0,
                  drawPoints: true,
                  pointSize: 4,
                  highlightCircleSize: 6
                },
                'line': {
                  strokeWidth: 1.0,
                  drawPoints: true,
                  pointSize: 1.5
                },
                'sine wave': {
                  strokeWidth: 3,
                  highlightCircleSize: 10
                }
              }
          );
    }
  });
