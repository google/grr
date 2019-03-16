/**
 * @license
 * Copyright 2013 David Eberlein (david.eberlein@ch.sauter-bc.com)
 * MIT-licensed (http://opensource.org/licenses/MIT)
 */

/**
 * @fileoverview DataHandler implementation for the fractions option.
 * @author David Eberlein (david.eberlein@ch.sauter-bc.com)
 */

(function() {

/*global Dygraph:false */
"use strict";

/**
 * @extends Dygraph.DataHandlers.DefaultHandler
 * @constructor
 */
Dygraph.DataHandlers.DefaultFractionHandler = function() {
};
  
var DefaultFractionHandler = Dygraph.DataHandlers.DefaultFractionHandler;
DefaultFractionHandler.prototype = new Dygraph.DataHandlers.DefaultHandler();

DefaultFractionHandler.prototype.extractSeries = function(rawData, i, options) {
  // TODO(danvk): pre-allocate series here.
  var series = [];
  var x, y, point, num, den, value;
  var mult = 100.0;
  var logScale = options.get('logscale');
  for ( var j = 0; j < rawData.length; j++) {
    x = rawData[j][0];
    point = rawData[j][i];
    if (logScale && point !== null) {
      // On the log scale, points less than zero do not exist.
      // This will create a gap in the chart.
      if (point[0] <= 0 || point[1] <= 0) {
        point = null;
      }
    }
    // Extract to the unified data format.
    if (point !== null) {
      num = point[0];
      den = point[1];
      if (num !== null && !isNaN(num)) {
        value = den ? num / den : 0.0;
        y = mult * value;
        // preserve original values in extras for further filtering
        series.push([ x, y, [ num, den ] ]);
      } else {
        series.push([ x, num, [ num, den ] ]);
      }
    } else {
      series.push([ x, null, [ null, null ] ]);
    }
  }
  return series;
};

DefaultFractionHandler.prototype.rollingAverage = function(originalData, rollPeriod,
    options) {
  rollPeriod = Math.min(rollPeriod, originalData.length);
  var rollingData = [];

  var i;
  var num = 0;
  var den = 0; // numerator/denominator
  var mult = 100.0;
  for (i = 0; i < originalData.length; i++) {
    num += originalData[i][2][0];
    den += originalData[i][2][1];
    if (i - rollPeriod >= 0) {
      num -= originalData[i - rollPeriod][2][0];
      den -= originalData[i - rollPeriod][2][1];
    }

    var date = originalData[i][0];
    var value = den ? num / den : 0.0;
    rollingData[i] = [ date, mult * value ];
  }

  return rollingData;
};

})();
