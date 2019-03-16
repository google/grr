/**
 * @license
 * Copyright 2013 David Eberlein (david.eberlein@ch.sauter-bc.com)
 * MIT-licensed (http://opensource.org/licenses/MIT)
 */

/**
 * @fileoverview DataHandler implementation for the combination 
 * of error bars and fractions options.
 * @author David Eberlein (david.eberlein@ch.sauter-bc.com)
 */

(function() {

/*global Dygraph:false */
"use strict";

/**
 * @constructor
 * @extends Dygraph.DataHandlers.BarsHandler
 */
Dygraph.DataHandlers.FractionsBarsHandler = function() {
};

var FractionsBarsHandler = Dygraph.DataHandlers.FractionsBarsHandler;
FractionsBarsHandler.prototype = new Dygraph.DataHandlers.BarsHandler();

/** @inheritDoc */
FractionsBarsHandler.prototype.extractSeries = function(rawData, i, options) {
  // TODO(danvk): pre-allocate series here.
  var series = [];
  var x, y, point, num, den, value, stddev, variance;
  var mult = 100.0;
  var sigma = options.get("sigma");
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
        stddev = den ? sigma * Math.sqrt(value * (1 - value) / den) : 1.0;
        variance = mult * stddev;
        y = mult * value;
        // preserve original values in extras for further filtering
        series.push([ x, y, [ y - variance, y + variance, num, den ] ]);
      } else {
        series.push([ x, num, [ num, num, num, den ] ]);
      }
    } else {
      series.push([ x, null, [ null, null, null, null ] ]);
    }
  }
  return series;
};

/** @inheritDoc */
FractionsBarsHandler.prototype.rollingAverage =
    function(originalData, rollPeriod, options) {
  rollPeriod = Math.min(rollPeriod, originalData.length);
  var rollingData = [];
  var sigma = options.get("sigma");
  var wilsonInterval = options.get("wilsonInterval");

  var low, high, i, stddev;
  var num = 0;
  var den = 0; // numerator/denominator
  var mult = 100.0;
  for (i = 0; i < originalData.length; i++) {
    num += originalData[i][2][2];
    den += originalData[i][2][3];
    if (i - rollPeriod >= 0) {
      num -= originalData[i - rollPeriod][2][2];
      den -= originalData[i - rollPeriod][2][3];
    }

    var date = originalData[i][0];
    var value = den ? num / den : 0.0;
    if (wilsonInterval) {
      // For more details on this confidence interval, see:
      // http://en.wikipedia.org/wiki/Binomial_confidence_interval
      if (den) {
        var p = value < 0 ? 0 : value, n = den;
        var pm = sigma * Math.sqrt(p * (1 - p) / n + sigma * sigma / (4 * n * n));
        var denom = 1 + sigma * sigma / den;
        low = (p + sigma * sigma / (2 * den) - pm) / denom;
        high = (p + sigma * sigma / (2 * den) + pm) / denom;
        rollingData[i] = [ date, p * mult,
            [ low * mult, high * mult ] ];
      } else {
        rollingData[i] = [ date, 0, [ 0, 0 ] ];
      }
    } else {
      stddev = den ? sigma * Math.sqrt(value * (1 - value) / den) : 1.0;
      rollingData[i] = [ date, mult * value, 
                         [ mult * (value - stddev), mult * (value + stddev) ] ];
    }
  }

  return rollingData;
};

})();
