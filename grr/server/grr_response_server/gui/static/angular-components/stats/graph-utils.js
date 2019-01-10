goog.module('grrUi.stats.graphUtils');
goog.module.declareLegacyNamespace();


/**
 * Builds a timeseries graph in given elements with given data.
 *
 * @param {!angular.jQuery} graphDiv Where the graph should be rendered.
 * @param {!angular.jQuery|undefined} legendDiv Where the graph legend should be
 *     rendered.
 * @param {!Object} seriesDict Graph data.
 * @returns {!Object} Dygraph instance.
 */
exports.buildTimeseriesGraph = function(graphDiv, legendDiv, seriesDict) {
  const labels = ['Time'];

  const dataMap = new Map();
  for (var label in seriesDict) {
    var serie = seriesDict[label];
    labels.push(label);

    angular.forEach(serie, (dataPoint) => {
      let entry = dataMap.get(dataPoint[0]);
      if (entry === undefined) {
        entry = {};
        dataMap.set(dataPoint[0], entry);
      }
      entry[label] = dataPoint[1];
    });
  }

  const timestamps = Array.from(dataMap.keys());
  timestamps.sort();

  const data = [];
  angular.forEach(timestamps, (t) => {
    const row = [new Date(t)];
    const timestampData = dataMap.get(t);
    for (let i = 1; i < labels.length; ++i) {
      row.push(timestampData[labels[i]]);
    }
    data.push(row);
  });

  return new Dygraph(graphDiv[0],
                     data,
                     {
                       animatedZoom: true,
                       labels: labels,
                       labelsDiv: legendDiv ? legendDiv[0] : undefined,
                       connectSeparatedPoints: true,
                       labelsSeparateLines: true,
                       highlightSeriesOpts: {
                         strokeWidth: 2,
                         strokeBorderWidth: 1,
                         highlightCircleSize: 5,
                       },
                       highlightCircleSize: 2,
                       strokeBorderWidth: 1,
                       axes: {
                         x: {
                           valueFormatter: (ms) => {
                             return new Date(ms).toUTCString();
                           }
                         }
                       }
                     });
};
