/*global Gallery,Dygraph,data */
Gallery.register(
  'link-interaction',
  {
    name: 'Link Interaction',
    setup: function(parent) {
      parent.innerHTML = [
          "<div id='div_g'></div>",
          "<b>Zoom:</b>",
          "<a href='#' id='hour'>hour</a> ",
          "<a href='#' id='day'>day</a> ",
          "<a href='#' id='week'>week</a> ",
          "<a href='#' id='month'>month</a> ",
          "<a href='#' id='full'>full</a> ",
          "<b>Pan:</b> ",
          "<a href='#' id='left'>left</a> ",
          "<a href='#' id='right'>right</a> "].join("\n");
    },
    run: function() {
      var r = [ ];
      var base_time = Date.parse("2008/07/01");
      var num = 24 * 0.25 * 365;
      for (var i = 0; i < num; i++) {
        r.push([ new Date(base_time + i * 3600 * 1000),
                 i + 50 * (i % 60),        // line
                 i * (num - i) * 4.0 / num  // parabola
               ]);
      }
      var orig_range = [ r[0][0].valueOf(), r[r.length - 1][0].valueOf() ];
      var g = new Dygraph(
            document.getElementById("div_g"),
            r, {
              rollPeriod: 7,
              animatedZooms: true,
              // errorBars: true,
              width: 600,
              height: 300,
              labels: ["Date", "a", "b"]
            }
          );

      var desired_range = null, animate;
      function approach_range() {
        if (!desired_range) return;
        // go halfway there
        var range = g.xAxisRange();
        if (Math.abs(desired_range[0] - range[0]) < 60 &&
            Math.abs(desired_range[1] - range[1]) < 60) {
          g.updateOptions({dateWindow: desired_range});
          // (do not set another timeout.)
        } else {
          var new_range;
          new_range = [0.5 * (desired_range[0] + range[0]),
                       0.5 * (desired_range[1] + range[1])];
          g.updateOptions({dateWindow: new_range});
          animate();
        }
      }
      animate = function() {
        setTimeout(approach_range, 50);
      };

      var zoom = function(res) {
        var w = g.xAxisRange();
        desired_range = [ w[0], w[0] + res * 1000 ];
        animate();
      };

      var reset = function() {
        desired_range = orig_range;
        animate();
      };

      var pan = function(dir) {
        var w = g.xAxisRange();
        var scale = w[1] - w[0];
        var amount = scale * 0.25 * dir;
        desired_range = [ w[0] + amount, w[1] + amount ];
        animate();
      };

      document.getElementById('hour').onclick = function() { zoom(3600); };
      document.getElementById('day').onclick = function() { zoom(86400); };
      document.getElementById('week').onclick = function() { zoom(604800); };
      document.getElementById('month').onclick = function() { zoom(30 * 86400); };
      document.getElementById('full').onclick = function() { reset(); };
      document.getElementById('left').onclick = function() { pan(-1); };
      document.getElementById('right').onclick = function() { pan(+1); };
    }
  });
