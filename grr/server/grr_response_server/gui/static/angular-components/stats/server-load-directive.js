'use strict';

goog.module('grrUi.stats.serverLoadDirective');
goog.module.declareLegacyNamespace();

const {ApiService} = goog.require('grrUi.core.apiService');


/**
 * Service for doing health indicators-related queries.
 *
 * @param {!angular.$q} $q
 * @param {!ApiService} grrApiService
 *
 * @constructor
 * @ngInject
 * @export
 */
exports.ServerLoadIndicatorService = function($q, grrApiService) {
  /** @private {!angular.$q} */
  this.q_ = $q;

  /** @private {!ApiService} */
  this.grrApiService_ = grrApiService;
};
var ServerLoadIndicatorService = exports.ServerLoadIndicatorService;


/**
 * Name of the service in Angular.
 */
ServerLoadIndicatorService.service_name = 'grrServerLoadIndicatorService';


/**
 * Calculates mean value of the response time series.
 *
 * @param {!Array<Array<number>>} timeseries Timeseries used to calculate
 *      mean value. Timeseries is a sequence of (timestamp, value) pairs.
 * @return {number} Mean value of the timeseries.
 *
 * @private
 */
ServerLoadIndicatorService.prototype.calculateMean_ = function(timeseries) {
  if (timeseries.length == 0) {
    return 0;
  }

  var result = 0;
  for (var i = 0; i < timeseries.length; ++i) {
    var dataPoint = timeseries[i];

    // Every data point should be a (timestamp, value) pair.
    if (dataPoint.length != 2) {
      throw new Error('Invalid data: timeseries data point is not an array ' +
          'with 2 numbers.');
    }

    result += dataPoint[1];
  }

  return result / timeseries.length;
};


/**
 * Fetch ratio indicator.
 *
 * @param {string} component Metric component.
 * @param {string} numeratorMetric Numerator metric.
 * @param {string} denominatorMetric Denominator metric.
 * @param {number} warningRatio If ratio value is above that and below danger
 *     level, status will be set to warning.
 * @param {number} dangerRatio If ratio value is above that, status will be set
 *     to danger.
 * @return {!angular.$q.Promise} Angular's promise that will resolve to a string
 *     with indicator's status.
 *
 * @export
 */
ServerLoadIndicatorService.prototype.fetchRatioIndicator = function(
    component, numeratorMetric, denominatorMetric, warningRatio, dangerRatio) {

  var endTime = Math.round(new Date().getTime() * 1000);
  var startTime = endTime - 10 * 60 * 1000000;
  var options = {
    start: startTime,
    end: endTime,
    aggregation: 'mean'
  };

  var metricsCache = {
    numerator: undefined,
    denominator: undefined
  };

  var deferred = this.q_.defer();

  var responseHandler = function(response) {
    if (response.data['metric_name'] == numeratorMetric) {
      metricsCache.numerator = this.calculateMean_(
          response.data['data_points']);
    } else if (response.data['metric_name'] == denominatorMetric) {
      metricsCache.denominator = this.calculateMean_(
          response.data['data_points']);
    } else {
      throw new Error('Unexpected metric name: ' +
          response.data['metric_name']);
    }

    if (angular.isDefined(metricsCache.numerator) &&
        angular.isDefined(metricsCache.denominator)) {
      if (metricsCache.denominator == 0) {
        deferred.resolve('unknown');
      } else {
        var ratio = metricsCache.numerator / metricsCache.denominator;
        if (ratio > dangerRatio) {
          deferred.resolve('danger');
        } else if (ratio > warningRatio) {
          deferred.resolve('warning');
        } else {
          deferred.resolve('normal');
        }
      }
    }
  };

  // Fetch numerator and denominator metrics.
  this.grrApiService_.get(
      'stats/store/' + component.toUpperCase() +
          '/metrics/' + numeratorMetric,
      options).then(responseHandler.bind(this));
  this.grrApiService_.get(
      'stats/store/' + component.toUpperCase() +
          '/metrics/' + denominatorMetric,
      options).then(responseHandler.bind(this));

  return deferred.promise;
};



/**
 * Controller for ServerLoadDirective.
 *
 * @constructor
 * @param {!angular.Scope} $scope
 * @param {!ServerLoadIndicatorService}
 *     grrServerLoadIndicatorService
 * @ngInject
 */
const ServerLoadController = function(
    $scope, grrServerLoadIndicatorService) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @private {!ServerLoadIndicatorService} */
  this.grrServerLoadIndicatorService_ = grrServerLoadIndicatorService;

  /** @export {number} Queries start time. */
  this.startTime;

  /** @export {number} Queries end time. */
  this.endTime;

  /** export {Object<string, string|angular.$q.Promise>} */
  this.indicators = {};

  /** @export {number} Max duration of graphs to show (in hours). */
  this.duration = 1;

  this.scope_.$watch('controller.duration', this.onDurationChange.bind(this));
};



/**
 * Handles changes of 'controller.duration' value.
 *
 * @param {number} newValue New duration value.
 * @export
 */
ServerLoadController.prototype.onDurationChange = function(newValue) {
  this.endTime = Math.round(new Date().getTime() * 1000);
  this.startTime = this.endTime - this.duration * 60 * 60 * 1000000;

  this.fetchIndicators_();
};


/**
 * Issues queries for metrics needed to display health indicators.
 *
 * @private
 */
ServerLoadController.prototype.fetchIndicators_ = function() {
  this.grrServerLoadIndicatorService_.fetchRatioIndicator(
      'frontend',                  // component name
      'frontend_active_count',     // numerator metric
      'frontend_max_active_count', // denominator metric
      0.35,                        // warning level
      0.75).then(function(result) {
        this.indicators['frontendLoad'] = result;
      }.bind(this));

  this.grrServerLoadIndicatorService_.fetchRatioIndicator(
      'worker',      // component name
      'grr_threadpool_outstanding_tasks',  // numerator
      'grr_threadpool_threads',  // denominator
      4,   // warning level
      10).then(function(result) {
        this.indicators['workerLoad'] = result;
      }.bind(this));
};



/**
 * Directive for displaying server load dashboard.
 *
 * @return {!angular.Directive} Directive definition object.
 * @ngInject
 * @export
 */
exports.ServerLoadDirective = function() {
  return {
    scope: {
    },
    restrict: 'E',
    templateUrl: '/static/angular-components/stats/server-load.html',
    controller: ServerLoadController,
    controllerAs: 'controller'
  };
};


/**
 * Directive's name in Angular.
 *
 * @const
 * @export
 */
exports.ServerLoadDirective.directive_name = 'grrServerLoad';
