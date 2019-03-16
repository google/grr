/*global Gallery,Dygraph,data */
Gallery.register(
  'two-axes',
  {
    name: "Multiple y-axes",
    setup: function(parent) {
      parent.innerHTML =
          "<p>The same data with both one and two y-axes. Two y-axes:</p>" +
          "<div id='demodiv' style='width: 640; height: 350; border: 1px solid black'></div>" +
          "<p>A single y-axis:</p>" +
          "<div id='demodiv_one' style='width: 640; height: 350; border: 1px solid black'></div>" +
          "<input type='checkbox' id='check'><label for='check'> Fill?</label>";
    },
    run: function() {
      var g, g2;
      document.getElementById('check').onchange = function(el) {
        g.updateOptions( { fillGraph: el.checked } );
        g2.updateOptions( { fillGraph: el.checked } );
      };

      var data = [];
      for (var i = 1; i <= 100; i++) {
        var m = "01", d = i;
        if (d > 31) { m = "02"; d -= 31; }
        if (m == "02" && d > 28) { m = "03"; d -= 28; }
        if (m == "03" && d > 31) { m = "04"; d -= 31; }
        if (d < 10) d = "0" + d;
        // two series, one with range 1-100, one with range 1-2M
        data.push([new Date("2010/" + m + "/" + d),
                   i,
                   100 - i,
                   1e6 * (1 + i * (100 - i) / (50 * 50)),
                   1e6 * (2 - i * (100 - i) / (50 * 50))]);
      }

      g = new Dygraph(
          document.getElementById("demodiv"),
          data,
          {
            labels: [ 'Date', 'Y1', 'Y2', 'Y3', 'Y4' ],
            'Y3': {
              axis: {
              }
            },
            'Y4': {
              axis: 'Y3'  // use the same y-axis as series Y3
            },
            axes: {
              y2: {
                // set axis-related properties here
                labelsKMB: true
              }
            },
            ylabel: 'Primary y-axis',
            y2label: 'Secondary y-axis',
            yAxisLabelWidth: 60
          }
      );

      g2 = new Dygraph(
          document.getElementById("demodiv_one"),
          data,
          {
            labels: [ 'Date', 'Y1', 'Y2', 'Y3', 'Y4' ],
            labelsKMB: true,
            ylabel: 'Primary y-axis',
            y2label: 'Secondary y-axis'
          }
      );
    }
  });
