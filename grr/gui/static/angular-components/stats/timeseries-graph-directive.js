'use strict';

goog.module('grrUi.stats.timeseriesGraphDirective');
goog.module.declareLegacyNamespace();



/** @typedef {{
 *             label:string,
 *             requestPath:string,
 *             requestOptions:Object
 *           }}
 */
let TimeserieDescriptor;

/**
 * Controller for TimeseriesGraphDirective.
 *
 * @constructor
 * @param {!angular.Scope} $scope
 * @param {!angular.jQuery} $element Element this directive operates on.
 * @param {!angular.$interval} $interval
 * @param {!grrUi.core.apiService.ApiService} grrApiService
 * @ngInject
 */
const TimeseriesGraphController = function(
    $scope, $element, $interval, grrApiService) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @private {!angular.jQuery} */
  this.element_ = $element;

  /** @private {!angular.$interval} */
  this.interval_ = $interval;

  /** @private {!grrUi.core.apiService.ApiService} */
  this.grrApiService_ = grrApiService;

  /** @export {Array.<number>} */
  this.timeRange = [NaN, NaN];

  /** @export {Array.<TimeserieDescriptor>} */
  this.seriesDescriptors = [];

  /** @export {!Object.<string, Object>} */
  this.fetchedSeries = {};

  /** @export {boolean} */
  this.inProgress = false;

  this.scope_.$watch('startTime', this.onStartTimeChange_.bind(this));
  this.scope_.$watch('endTime', this.onEndTimeChange_.bind(this));
  this.scope_.$watch('controller.timeRange',
                     this.onConfigurationChange_.bind(this),
                     true);
  this.scope_.$watch('controller.seriesDescriptors',
                     this.onConfigurationChange_.bind(this),
                     true);
};



/**
 * Handles changes of the start time scope attribute.
 *
 * @param {number} newValue new start time value.
 *
 * @private
 */
TimeseriesGraphController.prototype.onStartTimeChange_ = function(newValue) {
  this.timeRange[0] = newValue;
};


/**
 * Handles changes of the end time scope attribute.
 *
 * @param {number} newValue new end time value.
 *
 * @private
 */
TimeseriesGraphController.prototype.onEndTimeChange_ = function(newValue) {
  this.timeRange[1] = newValue;
};


/**
 * Converts timeserie of values to timeserie of deltas (in-place).
 *
 * @param {Array.<Array<number>>} points
 * @private
 */
TimeseriesGraphController.prototype.computeDelta_ = function(points) {
  if (points.length < 2) {
    return;
  }

  var prevPointValue = points.shift()[1];
  for (var i = 0; i < points.length; ++i) {
    var pointValue = points[i][1];
    points[i][1] = points[i][1] - prevPointValue;
    prevPointValue = pointValue;
  }
};


/**
 * Handles changes of time range or series descriptors. Start and end time
 * values are intentionally stored in time range array, so that if both start
 * and end times change during one apply/digest cycle, the change-handler
 * will be called only once. This way no extra HTTP requests will
 * be issued.
 *
 * @private
 */
TimeseriesGraphController.prototype.onConfigurationChange_ = function() {
  this.inProgress = true;
  this.fetchedSeries = {};

  angular.forEach(this.seriesDescriptors, function(descriptor) {
    var options = {
      start: this.timeRange[0],
      end: this.timeRange[1]
    };
    angular.extend(options, descriptor.requestOptions || {});

    var prevTimeRange = this.timeRange.slice();
    this.grrApiService_.get(descriptor.requestPath, options).then(
        function(response) {
          // Check that these data actually correspond to the
          // request we've sent.
          if (angular.equals(prevTimeRange, this.timeRange)) {
            var serie = response['data'];
            serie['data_points'] = serie['data_points'] || [];

            if (this.scope_['computeDelta']) {
              this.computeDelta_(serie['data_points']);
            }

            this.fetchedSeries[descriptor.label] = serie;
            this.buildGraphIfNeeded_();
          }
        }.bind(this));
  }.bind(this));
};


/**
 * Adds new timeseries specification. Called by nested
 * TimeseriesGraphSerie directives.
 *
 * @param {!TimeserieDescriptor} descriptor
 * @export
 */
TimeseriesGraphController.prototype.addSerieDescriptor = function(descriptor) {
  this.seriesDescriptors.push(descriptor);
};


/**
 * Builds the graph if all the data are fetched.
 *
 * @private
 */
TimeseriesGraphController.prototype.buildGraphIfNeeded_ = function() {
  if (Object.keys(this.fetchedSeries).length == this.seriesDescriptors.length) {
    this.inProgress = false;

    var data = [];
    for (var label in this.fetchedSeries) {
      var item = this.fetchedSeries[label];
      data.push({
        label: label,
        data: item['data_points']
      });
    }

    var config = {
      xaxis: {
        mode: 'time',
        axisLabel: 'Time'
      },
      yaxis: {
        axisLabel: label
      }
    };

    // Wait until timeseries-graph appears and draw the graph.
    var intervalPromise = this.interval_(function() {
      var graphElement = $(this.element_).find('.timeseries-graph');
      if (graphElement) {
        $.plot(graphElement, data, config);
        this.interval_.cancel(intervalPromise);
      }
    }.bind(this), 500, 10);
  }
};



/**
 * Directive for displaying a timeseries graph. This directive is
 * configured by nested directives that register timeseries (see
 * grr-server-load-graph-serie, for example).
 *
 * @return {angular.Directive} Directive definition object.
 * @export
 */
exports.TimeseriesGraphDirective = function() {
  return {
    scope: {
      title: '@',
      computeDelta: '@',
      startTime: '=',
      endTime: '='
    },
    restrict: 'E',
    templateUrl: '/static/angular-components/stats/timeseries-graph.html',
    transclude: true,
    controller: TimeseriesGraphController,
    controllerAs: 'controller'
  };
};


/**
 * Directive's name in Angular.
 *
 * @const
 * @export
 */
exports.TimeseriesGraphDirective.directive_name = 'grrTimeseriesGraph';
