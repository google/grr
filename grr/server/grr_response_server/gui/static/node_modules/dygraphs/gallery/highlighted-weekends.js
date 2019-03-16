/*global Gallery,Dygraph,data */
Gallery.register(
  'highlighted-weekends',
  {
    name: 'Highlighted Weekends',
    title: 'Draws a time series with weekends highlighted',
    setup: function(parent) {
      parent.innerHTML = [
        "<div id='div_g' style='width:600px; height:300px;'></div>",
        "<p>When you zoom and pan, the weekend regions remain highlighted.</p>"].join("\n");
    },
    run: function() {
      // Some sample data
      var data = "2011-01-01," + Math.random()*100 + "\n" +
        "2011-01-02," + Math.random()*100 + "\n" +
        "2011-01-03," + Math.random()*100 + "\n" +
        "2011-01-04," + Math.random()*100 + "\n" +
        "2011-01-05," + Math.random()*100 + "\n" +
        "2011-01-06," + Math.random()*100 + "\n" +
        "2011-01-07," + Math.random()*100 + "\n" +
        "2011-01-08," + Math.random()*100 + "\n" +
        "2011-01-09," + Math.random()*100 + "\n" +
        "2011-01-10," + Math.random()*100 + "\n" +
        "2011-01-11," + Math.random()*100 + "\n" +
        "2011-01-12," + Math.random()*100 + "\n" +
        "2011-01-13," + Math.random()*100 + "\n" +
        "2011-01-14," + Math.random()*100 + "\n" +
        "2011-01-15," + Math.random()*100 + "\n" +
        "2011-01-16," + Math.random()*100 + "\n" +
        "2011-01-17," + Math.random()*100 + "\n" +
        "2011-01-18," + Math.random()*100 + "\n" +
        "2011-01-19," + Math.random()*100 + "\n" +
        "2011-01-20," + Math.random()*100 + "\n" +
        "2011-01-21," + Math.random()*100 + "\n" +
        "2011-01-22," + Math.random()*100 + "\n" +
        "2011-01-23," + Math.random()*100 + "\n" +
        "2011-01-24," + Math.random()*100 + "\n" +
        "2011-01-25," + Math.random()*100 + "\n" +
        "2011-01-26," + Math.random()*100 + "\n" +
        "2011-01-27," + Math.random()*100 + "\n" +
        "2011-01-28," + Math.random()*100 + "\n" +
        "2011-01-29," + Math.random()*100 + "\n" +
        "2011-01-30," + Math.random()*100 + "\n" +
        "2011-01-31," + Math.random()*100 + "\n";

      new Dygraph(
        document.getElementById("div_g"),
        data,
        {
          labels: ['Date','Value'],
          underlayCallback: function(canvas, area, g) {

            canvas.fillStyle = "rgba(255, 255, 102, 1.0)";

            function highlight_period(x_start, x_end) {
              var canvas_left_x = g.toDomXCoord(x_start);
              var canvas_right_x = g.toDomXCoord(x_end);
              var canvas_width = canvas_right_x - canvas_left_x;
              canvas.fillRect(canvas_left_x, area.y, canvas_width, area.h);
            }

            var min_data_x = g.getValue(0,0);
            var max_data_x = g.getValue(g.numRows()-1,0);

            // get day of week
            var d = new Date(min_data_x);
            var dow = d.getUTCDay();

            var w = min_data_x;
            // starting on Sunday is a special case
            if (dow === 0) {
              highlight_period(w,w+12*3600*1000);
            }
            // find first saturday
            while (dow != 6) {
              w += 24*3600*1000;
              d = new Date(w);
              dow = d.getUTCDay();
            }
            // shift back 1/2 day to center highlight around the point for the day
            w -= 12*3600*1000;
            while (w < max_data_x) {
              var start_x_highlight = w;
              var end_x_highlight = w + 2*24*3600*1000;
              // make sure we don't try to plot outside the graph
              if (start_x_highlight < min_data_x) {
                start_x_highlight = min_data_x;
              }
              if (end_x_highlight > max_data_x) {
                end_x_highlight = max_data_x;
              }
              highlight_period(start_x_highlight,end_x_highlight);
              // calculate start of highlight for next Saturday 
              w += 7*24*3600*1000;
            }
          }
        });
    }
  });
