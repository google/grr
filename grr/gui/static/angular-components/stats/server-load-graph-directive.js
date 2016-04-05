'use strict';

goog.provide('grrUi.stats.serverLoadGraphDirective.ServerLoadGraphController');
goog.provide('grrUi.stats.serverLoadGraphDirective.ServerLoadGraphDirective');
goog.provide('grrUi.stats.serverLoadGraphDirective.ServerLoadGraphSerieDirective');

goog.scope(function() {



/**
 * Controller for ServerLoadGraphDirective.
 *
 * @constructor
 * @param {!angular.Scope} $scope
 * @param {!angular.jQuery} $element Element this directive operates on.
 * @param {!angular.$interval} $interval
 * @param {!grrUi.core.apiService.ApiService} grrApiService
 * @ngInject
 */
grrUi.stats.serverLoadGraphDirective.ServerLoadGraphController = function(
    $scope, $element, $interval, grrApiService) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @private {!angular.jQuery} */
  this.element_ = $element;

  /** @private {!angular.$interval} */
  this.interval_ = $interval;

  /** @private {!grrUi.core.apiService.ApiService} */
  this.grrApiService_ = grrApiService;

  /** @export {Array.<Number>} */
  this.timeRange = [NaN, NaN];

  /** @export {Array.<Object>} */
  this.series = [];

  /** @export {!Object.<string, Object>} */
  this.fetchedSeries = {};

  /** @export {boolean} */
  this.inProgress = false;

  this.scope_.$watch('startTime', this.onStartTimeChange_.bind(this));
  this.scope_.$watch('endTime', this.onEndTimeChange_.bind(this));
  this.scope_.$watchCollection('controller.timeRange',
                               this.onTimeRangeChange_.bind(this));
};

var ServerLoadGraphController =
    grrUi.stats.serverLoadGraphDirective.ServerLoadGraphController;


/**
 * Handles changes of the start time scope attribute.
 *
 * @param {Number} newValue new start time value.
 *
 * @private
 */
ServerLoadGraphController.prototype.onStartTimeChange_ = function(newValue) {
  this.timeRange[0] = newValue;
};


/**
 * Handles changes of the end time scope attribute.
 *
 * @param {Number} newValue new end time value.
 *
 * @private
 */
ServerLoadGraphController.prototype.onEndTimeChange_ = function(newValue) {
  this.timeRange[1] = newValue;
};


/**
 * Handles changes of time range attribute. Start and end time values are
 * intentionally stored in time range array, so that if both start and
 * end times change during one apply/digest cycle, the change-handler
 * will be called only once. This way no extra HTTP requests will
 * be issued.
 *
 * @private
 */
ServerLoadGraphController.prototype.onTimeRangeChange_ = function() {
  this.inProgress = true;
  this.fetchedSeries = {};

  angular.forEach(this.series, function(item) {
    var options = {
      start: this.timeRange[0],
      end: this.timeRange[1]
    };
    if (item.distributionHandling) {
      options['distribution_handling_mode'] = item.distributionHandling;
    }
    if (item.aggregation) {
      options['aggregation_mode'] = item.aggregation;
    }
    if (item.rate) {
      options['rate'] = item.rate;
    }

    var prevTimeRange = this.timeRange.slice();
    this.grrApiService_.get('stats/store/' +
        item.component.toUpperCase() +
        '/metrics/' + item.metric, options).then(
            function(response) {
              // Check that these data actually correspond to the
              // request we've sent.
              if (angular.equals(prevTimeRange, this.timeRange)) {
                this.fetchedSeries[item.label] = response.data;
                this.buildGraphIfNeeded_();
              }
            }.bind(this));
  }.bind(this));
};


/**
 * Adds new timeseries specification. Called by nested
 * ServerLoadGraphSerie directives.
 *
 * @param {!Object} series Series spec to add.
 * @export
 */
ServerLoadGraphController.prototype.addSeries = function(series) {
  this.series.push(series);
};


/**
 * Builds the graph if all the data are fetched.
 *
 * @private
 */
ServerLoadGraphController.prototype.buildGraphIfNeeded_ = function() {
  if (Object.keys(this.fetchedSeries).length == this.series.length) {
    this.inProgress = false;

    var data = [];
    for (var label in this.fetchedSeries) {
      var item = this.fetchedSeries[label];
      data.push({
        label: label,
        data: item['timeseries']
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

    // Wait until server-load-graph appears and draw the graph.
    var intervalPromise = this.interval_(function() {
      var graphElement = $(this.element_).find('.server-load-graph');
      if (graphElement) {
        $.plot(graphElement, data, config);
        this.interval_.cancel(intervalPromise);
      }
    }.bind(this), 500, 10);
  }
};



/**
 * Directive for displaying a graph in the server load dashboard.
 *
 * @constructor
 * @ngInject
 * @export
 */
grrUi.stats.serverLoadGraphDirective.ServerLoadGraphDirective = function() {
  return {
    scope: {
      title: '@',
      startTime: '=',
      endTime: '='
    },
    restrict: 'E',
    templateUrl: '/static/angular-components/stats/server-load-graph.html',
    transclude: true,
    controller: ServerLoadGraphController,
    controllerAs: 'controller'
  };
};


/**
 * Directive's name in Angular.
 *
 * @const
 * @export
 */
grrUi.stats.serverLoadGraphDirective.ServerLoadGraphDirective.directive_name =
    'grrServerLoadGraph';



/**
 * Registers serie in the graph.
 *
 * @constructor
 * @ngInject
 * @export
 */
grrUi.stats.serverLoadGraphDirective.ServerLoadGraphSerieDirective =
    function() {
      return {
        scope: {
          component: '@',
          metric: '@',
          rate: '@',
          aggregation: '@',
          distributionHandling: '@',
          label: '@'
        },
        restrict: 'E',
        require: '^grrServerLoadGraph',
        link: function(scope, element, attrs, grrServerLoadGraphCtrl) {
          grrServerLoadGraphCtrl.addSeries(scope);
        }
      };
    };


/**
 * Name of the directive as registered in Angular.
 *
 * @const
 * @export
 */
grrUi.stats.serverLoadGraphDirective.
    ServerLoadGraphSerieDirective.directive_name = 'grrServerLoadGraphSerie';

});  // goog.scope
