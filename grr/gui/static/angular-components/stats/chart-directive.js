'use strict';

goog.provide('grrUi.stats.chartDirective.ChartController');
goog.provide('grrUi.stats.chartDirective.ChartDirective');

goog.require('grrUi.core.apiService.stripTypeInfo');

goog.scope(function() {

var stripTypeInfo = grrUi.core.apiService.stripTypeInfo;

/** @type {string} */
var DEFAULT_HOVER_TEXT = '';

/**
 * Controller for ChartDirective.
 *
 * @param {!angular.Scope} $scope
 * @param {!angular.jQuery} $element
 * @constructor
 * @ngInject
 */
grrUi.stats.chartDirective.ChartController = function(
    $scope, $element) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @private {!angular.jQuery} */
  this.element_ = $element;

  /** @private {!Object} */
  this.chartElement_ = this.element_.find('.chart');

  /** @private {!Object} */
  this.hoverElement_ = this.element_.find('.hover');

  /** @type {string} */
  this.hoverColor = '#000';

  /** @type {string} */
  this.hoverText = DEFAULT_HOVER_TEXT;

  /** @type {string} */
  this.errorMsg = '';

  this.scope_.$watch('data', function(data) {
    if (angular.isDefined(data)) {
      this.initChart_(data);
    }
  }.bind(this));
};
var ChartController = grrUi.stats.chartDirective.ChartController;


/**
 * Initializes the chart.
 *
 * @param {Object} data The data to be displayed.
 * @private
 */
ChartController.prototype.initChart_ = function(data) {
  this.hoverText = DEFAULT_HOVER_TEXT;

  switch (data['representation_type']) {
  case 'STACK_CHART':
    this.initStackChart_(data['stack_chart']);
    break;
  case 'PIE_CHART':
    this.initPieChart_(data['pie_chart']);
    break;
  //TODO(user): Implement cases for other chart types.
  default:
    this.errorMsg = 'Unexpected representation type.';
  }
};

/**
 * Initializes a stack chart.
 *
 * @param {Object} stackChartData The data to be displayed.
 * @private
 */
ChartController.prototype.initStackChart_ = function(stackChartData) {
  if (stackChartData['data'].length == 0) {
    this.errorMsg = 'No data to display.';
    return;
  }

  var specs = stackChartData['data'].map(function(series) {
    return {
      label: series['label'],
      data: series['points'].map(function(point) {
        return [
          point['x'],
          point['y']
        ];
      }.bind(this))
    };
  }.bind(this));

  this.chartElement_.resize(function() {
    this.chartElement_.html('');

    $.plot($(this.chartElement_), specs, {
      series: {
        stack: true,
        bars: {
          show: true,
          barWidth: 0.6
        },
        label: {
          show: true,
          radius: 0.5
        },
        background: { opacity: 0.8 }
      },
      grid: {
        hoverable: true,
        clickable: true
      }
    });
  }.bind(this));

  this.chartElement_.bind('plothover', function(event, pos, obj) {
    if (obj) {
      this.hoverColor = obj.series.color;
      this.hoverText = obj.series.label + ': ' +
                       (obj.datapoint[1] - obj.datapoint[2]);
    }
  }.bind(this));

  this.chartElement_.resize();
};

/**
 * Initializes a pie chart.
 *
 * @param {Object} pieChartData The data to be displayed.
 * @private
 */
ChartController.prototype.initPieChart_ = function(pieChartData) {
  if (pieChartData['data'].length == 0) {
    this.errorMsg = 'No data to display.';
    return;
  }

  var specs = pieChartData['data'].map(function(point) {
    return {
      label: point['label'],
      data: point['x']
    };
  }.bind(this));

  this.chartElement_.resize(function() {
    this.chartElement_.html('');

    $.plot($(this.chartElement_), specs, {
      series: {
        pie: {
          show: true,
          label: {
            show: true,
            radius: 0.5,
            formatter: function(label, series) {
              return ('<div class="pie-label">' +
                        label + '<br/>' +
                        Math.round(series['percent']) + '%' +
                      '</div>');
            },
            background: { opacity: 0.8 }
          }
        }
      },
      grid: {
        hoverable: true,
        clickable: true
      }
    });
  }.bind(this));

  this.chartElement_.bind('plothover', function(event, pos, obj) {
    if (obj) {
      var percent = parseFloat(obj.series.percent).toFixed(2);
      this.hoverColor = obj.series.color;
      this.hoverText = obj.series.label + ' ' +
                       obj.series.data[0][1] + ' (' + percent + '%)';
    }
  }.bind(this));

  this.chartElement_.resize();
};

/**
 * ChartDirective definition.
 *
 * @return {angular.Directive} Directive definition object.
 */
grrUi.stats.chartDirective.ChartDirective = function() {
  return {
    scope: {
      data: "="
    },
    restrict: 'E',
    templateUrl: '/static/angular-components/stats/chart.html',
    controller: ChartController,
    controllerAs: 'controller'
  };
};


/**
 * Name of the directive in Angular.
 *
 * @const
 * @export
 */
grrUi.stats.chartDirective.ChartDirective.directive_name =
    'grrChart';

});  // goog.scope
