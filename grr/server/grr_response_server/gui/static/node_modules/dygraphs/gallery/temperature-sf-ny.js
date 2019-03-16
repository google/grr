/*global Gallery,Dygraph,data */
/*global data_temp */
Gallery.register(
  // Get a better name.
  'temperature-sf-ny',
  {
    name: 'Roll Periods and Error Bars',
    title: 'Demo of a graph with many data points and custom error bars.',
    setup: function(parent) {
      parent.innerHTML = [
          "<p>Roll period of 14 timesteps.</p>",
          "<div id='roll14' style='width:600px; height:300px;'></div>",
          "<p>No roll period.</p>",
          "<div id='noroll' style='width:600px; height:300px;'></div>"]
          .join("\n");
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
            labelsDivStyles: { 'textAlign': 'right' }
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
            labelsDivStyles: { 'textAlign': 'right' }
          }
      );
    }
  });
