/*global Gallery,Dygraph,data */
Gallery.register(
  'demo',
  {
    name: 'Interesting Shapes',
    title: 'The original demo!',
    setup: function(parent) {
      parent.innerHTML =
        "<span style='font-size: small;'>(Mouse over to highlight individual values. Click and drag to zoom. Double-click to zoom out.)</span><br/>" +
        "<table><tr><td>" +
        "<div id='demodiv'></div>" +
        "</td><td valign=top>" +
        "<div id='status' style='width:200px; font-size:0.8em; padding-top:5px;'></div>" +
        "</td>" +
        "</tr></table>";
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
                labelsDiv: document.getElementById('status'),
                labelsSeparateLines: true,
                labelsKMB: true,
                legend: 'always',
                colors: ["rgb(51,204,204)",
                         "rgb(255,100,100)",
                         "#00DD55",
                         "rgba(50,50,200,0.4)"],
                width: 640,
                height: 480,
                title: 'Interesting Shapes',
                xlabel: 'Date',
                ylabel: 'Count',
                axisLineColor: 'white',
                drawXGrid: false
              }
        );
    }
  });
