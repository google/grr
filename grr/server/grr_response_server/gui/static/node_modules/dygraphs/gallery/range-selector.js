/*global Gallery,Dygraph,data */
/*global data_temp */
Gallery.register(
  'range-selector',
  {
    name: 'Range Selector',
    title: 'Demo of the Range Selector',
    setup: function(parent) {
      parent.innerHTML = [
          "<p>No roll period.</p>",
          "<div id='noroll' style='width:600px; height:300px;'></div>",
          "",
          "<p>Roll period of 14 timesteps, custom range selector height and plot color.</p>",
          "<div id='roll14' style='width:600px; height:300px;'></div>"].join("\n");
    },
    run: function() {
      new Dygraph(
          document.getElementById("noroll"),
          data_temp,
          {
            customBars: true,
            title: 'Daily Temperatures in New York vs. San Francisco',
            ylabel: 'Temperature (F)',
            legend: 'always',
            labelsDivStyles: { 'textAlign': 'right' },
            showRangeSelector: true
          }
      );
      new Dygraph(
          document.getElementById("roll14"),
          data_temp,
          {
            rollPeriod: 14,
            showRoller: true,
            customBars: true,
            title: 'Daily Temperatures in New York vs. San Francisco',
            ylabel: 'Temperature (F)',
            legend: 'always',
            labelsDivStyles: { 'textAlign': 'right' },
            showRangeSelector: true,
            rangeSelectorHeight: 30,
            rangeSelectorPlotStrokeColor: 'yellow',
            rangeSelectorPlotFillColor: 'lightyellow'
          });
    }
  });
