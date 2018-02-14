'use strict';

goog.module('grrUi.hunt.huntStatsDirective');
goog.module.declareLegacyNamespace();

const {ApiService, stripTypeInfo} = goog.require('grrUi.core.apiService');


/**
 * Controller for HuntStatsDirective.
 *
 * @constructor
 * @param {!angular.Scope} $scope
 * @param {!angular.jQuery} $element
 * @param {!ApiService} grrApiService
 * @ngInject
 */
const HuntStatsController = function(
    $scope, $element, grrApiService) {

  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @private {!angular.jQuery} */
  this.element_ = $element;

  /** @private {!ApiService} */
  this.grrApiService_ = grrApiService;

  /** @export {Object} */
  this.stats;

  /** @export {Object} */
  this.userCpuStats;

  /** @export {Object} */
  this.systemCpuStats;

  /** @export {Object} */
  this.networkBytesStats;

  /** @export {number} */
  this.totalClientCount;

  $scope.$watch('huntId', this.onHuntIdChange_.bind(this));
};



/**
 * Handles huntId attribute changes.
 * @param {string} huntId The newly set hunt urn.
 * @private
 */
HuntStatsController.prototype.onHuntIdChange_ = function(huntId) {
  if (!angular.isString(huntId)) {
    return;
  }

  var url = '/hunts/' + huntId + '/stats';
  this.grrApiService_.get(url).then(function success(response) {
    this.stats = response.data['stats'];

    var strippedStats = stripTypeInfo(this.stats);
    this.userCpuStats = this.parseStats_(strippedStats['user_cpu_stats'], null);
    this.systemCpuStats = this.parseStats_(strippedStats['system_cpu_stats'], null);
    this.networkBytesStats = this.parseStats_(strippedStats['network_bytes_sent_stats'], this.formatBytes_);

    if (strippedStats['user_cpu_stats']) {
      this.totalClientCount = strippedStats['user_cpu_stats']['num'];
    }

    this.drawHistograms_();
  }.bind(this));
};

/**
 * Formats byte values to properly display them on the x-axis of histogram.
 * @param {number} value The number of bytes.
 * @return {string} A string representation of the number of bytes.
 * @private
 */
HuntStatsController.prototype.formatBytes_ = function(value) {
  // TODO(user): Once we have the bytesFilter implemented, we can use it here.
  if (value < 1024) {
    return value + 'B';
  } else {
    return Math.round(value / 1024) + 'K';
  }
};

/**
 * Parses the running stats to a format better suited for displaying.
 * @param {!Object} stats A stat element.
 * @param {?function(number) : string} xAxisFormatter An optional formatter for x-axis labels.
 * @return {Object} An object holding properties for displaying.
 * @private
 */
HuntStatsController.prototype.parseStats_ = function(stats, xAxisFormatter){
  if (!stats) {
    return null;
  }

  var mean = 0;
  if (stats['num']) {
    mean = stats['sum'] / stats['num'];
  }

  var stdev = 0;
  if (stats['num']) {
    stdev = Math.sqrt(stats['sum_sq'] / stats['num'] - Math.pow(mean, 2));
  }

  var histogramData = [];
  var histogramTicks = [];
  angular.forEach(stats['histogram']['bins'], function(item, index) {
    var value = item['num'] || 0;
    histogramData.push([index, value]);

    var range = item['range_max_value'];
    var xValue = range % 1 != 0 ? range.toFixed(1) : range;
    if (xAxisFormatter) {
      xValue = xAxisFormatter(xValue);
    }
    histogramTicks.push([index + 0.5, xValue]); // +0.5 to center align the tick label.
  });

  return {
    mean: mean,
    stdev: stdev,
    histogram: {
      data: histogramData,
      ticks: histogramTicks
    }
  };
};

/**
 * Redraws the histograms.
 * @private
 */
HuntStatsController.prototype.drawHistograms_ = function() {
  if (this.userCpuStats) {
    var userCpuGraphElement = this.element_.find('.user-cpu-histogram');
    this.drawSingleHistogram_(userCpuGraphElement, this.userCpuStats.histogram);
  }

  if (this.systemCpuStats) {
    var systemCpuGraphElement = this.element_.find('.system-cpu-histogram');
    this.drawSingleHistogram_(systemCpuGraphElement, this.systemCpuStats.histogram);
  }

  if (this.networkBytesStats) {
    var networkBytesGraphElement = this.element_.find('.network-bytes-histogram');
    this.drawSingleHistogram_(networkBytesGraphElement, this.networkBytesStats.histogram);
  }
};

/**
 * Redraw a specific histogram.
 * @param {!jQuery} element The container element.
 * @param {!Object} histogram Contains the data for the histogram.
 * @private
 */
HuntStatsController.prototype.drawSingleHistogram_ = function(element, histogram) {
  $.plot(element, [{
    data: histogram['data'],
    bars: {
      show: true,
      lineWidth: 1
    }
  }], {
    xaxis: {
      tickLength: 0,
      ticks: histogram['ticks']
    },
    yaxis: {
      minTickSize: 1,
      tickDecimals: 0
    }
  });
};

/**
 * Directive for displaying stats of a hunt with a given URN.
 *
 * @return {!angular.Directive} Directive definition object.
 * @ngInject
 * @export
 */
exports.HuntStatsDirective = function() {
  return {
    scope: {
      huntId: '='
    },
    restrict: 'E',
    templateUrl: '/static/angular-components/hunt/hunt-stats.html',
    controller: HuntStatsController,
    controllerAs: 'controller'
  };
};


/**
 * Directive's name in Angular.
 *
 * @const
 * @export
 */
exports.HuntStatsDirective.directive_name = 'grrHuntStats';
