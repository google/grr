/*global Gallery,Dygraph,data */
Gallery.register(
  'styled-chart-labels',
  {
    name: 'CSS label styling',
    title: 'Each chart label is styled independently with CSS',
    setup: function(parent) {
      parent.innerHTML = [
          "<p class='infotext'>This chart's labels are styled</p>",
          "<div class='chart' id='div_g' style='width:600px; height:300px;'></div>",
          "<p class='infotext'>This version of the chart uses the default styles:</p>",
          "<div class='chart' id='div_g2' style='width:600px; height:300px;'></div>"].join("\n");
    },
    run: function() {
      new Dygraph(
            document.getElementById("div_g"),
            data, {
              rollPeriod: 7,
              legend: 'always',
              title: 'High and Low Temperatures',
              titleHeight: 32,
              ylabel: 'Temperature (F)',
              xlabel: 'Date (Ticks indicate the start of the indicated time period)',
              labelsDivStyles: {
                'text-align': 'right',
                'background': 'none'
              },
              strokeWidth: 1.5
            }
          );

      new Dygraph(
            document.getElementById("div_g2"),
            data, {
              rollPeriod: 30,
              legend: 'always',
              title: 'High and Low Temperatures (30-day average)',
              ylabel: 'Temperature (F)',
              xlabel: 'Date (Ticks indicate the start of the indicated time period)',
              labelsDivStyles: {
                'text-align': 'right',
                'background': 'none'
              },
              strokeWidth: 1.5
            }
          );
    }
  });
