goog.module('grrUi.hunt.huntStatsDirective');
goog.module.declareLegacyNamespace();

const {ApiService} = goog.require('grrUi.core.apiService');


/**
 * Controller for HuntStatsDirective.
 *
 * @constructor
 * @param {!angular.Scope} $scope
 * @param {!ApiService} grrApiService
 * @ngInject
 */
const HuntStatsController = function($scope, grrApiService) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

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

  this.scope_.$watch('huntId', x => this.onHuntIdChange_(x));
};


/**
 * Formats seconds to properly display them as histogram labels.
 *
 * @param {number} value The number of seconds.
 * @return {string} A string corresponding to a histogram label.
 * @private
 */
function formatSeconds(value) {
  return value.toFixed(1) + 's';
}

/**
 * Formats byte values to properly display them as histogram labels.
 *
 * @param {number} value The number of bytes.
 * @return {string} A string corresponding to a histogram label.
 * @private
 */
function formatBytes(value) {
  // TODO(user): Once we have the bytesFilter implemented, we can use it
  // here.
  if (value < 1024) {
    return `${value} B`;
  } else {
    return `${Math.round(value / 1024)} KiB`;
  }
}


/**
 * Convert histogram values returned by the API call to the format expected
 * by grr-comparison-chart directive.
 *
 * @param {!Object} data Source histogram data returned by
 *     /hunts/<hunt id>/stats API call.
 * @param {function(number):string} labelFormatFn Function to format histogram
 *     labels.
 * @return {!Object} Data structure suitable for grr-comparison-chart input.
 * @private
 */
HuntStatsController.prototype.convertHistogramToComparisonChart_ = function(
    data, labelFormatFn) {
  const series = [];
  let mean = undefined;
  let stddev = undefined;

  if (data !== undefined) {
    const bins = data['value']['histogram']['value']['bins'];
    for (const bin of bins) {
      let num = 0;
      if (bin['value']['num'] !== undefined) {
        num = bin['value']['num']['value'];
      }

      series.push({
        value: {
          label:
              {value: '< ' + labelFormatFn(bin['value']['range_max_value']['value'])},
          x: {value: num}
        }
      });
    }
    if (series.length > 0 && bins.length > 1) {
      const lastSerie = series[series.length - 1]['value'];
      lastSerie['label']['value'] = '> ' + labelFormatFn(
          bins[bins.length - 2]['value']['range_max_value']['value']);
    }

    if (data['value']['num']) {
      mean = data['value']['sum']['value'] / data['value']['num']['value'];
      stddev = data['value']['stddev']['value'];
    }
  }

  return {mean, stddev, value: {data: series}};
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

  var url = `/hunts/${huntId}/stats`;
  this.grrApiService_.get(url).then((response) => {
    this.stats = response.data['stats'];

    this.userCpuStats = this.convertHistogramToComparisonChart_(
        this.stats['value']['user_cpu_stats'], formatSeconds);
    this.systemCpuStats = this.convertHistogramToComparisonChart_(
        this.stats['value']['system_cpu_stats'], formatSeconds);
    this.networkBytesStats = this.convertHistogramToComparisonChart_(
        this.stats['value']['network_bytes_sent_stats'], formatBytes);

    if (this.stats['value']['user_cpu_stats']) {
      this.totalClientCount =
          this.stats['value']['user_cpu_stats']['num']['value'];
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
