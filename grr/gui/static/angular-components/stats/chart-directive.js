'use strict';

goog.module('grrUi.stats.chartDirective');
goog.module.declareLegacyNamespace();

const {stripTypeInfo} = goog.require('grrUi.core.apiService');



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
const ChartController = function(
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

  this.scope_.$watch('typedData', function() {
    var typedData = this.scope_['typedData'];

    if (angular.isDefined(typedData)) {
      var data = /** @type {Object} */ (stripTypeInfo(typedData));

      this.initChart_(data, typedData);
    }
  }.bind(this));
};


/**
 * Initializes the chart.
 *
 * @param {Object} data The data to be displayed.
 * @param {Object} typedData The data to be displayed, with type annotations.
 * @private
 */
ChartController.prototype.initChart_ = function(data, typedData) {
  this.hoverText = DEFAULT_HOVER_TEXT;
  this.errorMsg = '';

  switch (data['representation_type']) {
  case 'STACK_CHART':
    this.initStackChart_(data['stack_chart']);
    break;
  case 'PIE_CHART':
    this.initPieChart_(data['pie_chart']);
    break;
  case 'LINE_CHART':
    this.initLineChart_(data['line_chart']);
    break;
  case 'AUDIT_CHART':
    // Noop.
    break;
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
  if (angular.isUndefined(stackChartData['data']) ||
      stackChartData['data'].length == 0) {
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

  // Converts ApiReportTickSpecifier to Flot-supported format.
  var extractTicks = function(protoTick) {
    return [protoTick['x'],
            protoTick['label']];
  }.bind(this);

  var x_ticks = undefined;
  var y_ticks = undefined;

  if (angular.isDefined(stackChartData['x_ticks'])) {
    x_ticks = stackChartData['x_ticks'].map(extractTicks);
  }

  if (angular.isDefined(stackChartData['y_ticks'])) {
    y_ticks = stackChartData['y_ticks'].map(extractTicks);
  }

  var barWidth = stackChartData['bar_width'] || .6;

  this.chartElement_.resize(function() {
    this.chartElement_.html('');

    $.plot($(this.chartElement_), specs, {
      series: {
        stack: true,
        bars: {
          show: true,
          barWidth: barWidth
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
      },
      xaxis: {
        min: 0,
        ticks: x_ticks,
      },
      yaxis: {
        min: 0,
        ticks: y_ticks,
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
  if (angular.isUndefined(pieChartData['data']) ||
      pieChartData['data'].length == 0) {
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
 * Initializes a line chart.
 *
 * @param {Object} lineChartData The data to be displayed.
 * @private
 */
ChartController.prototype.initLineChart_ = function(lineChartData) {
  if (angular.isUndefined(lineChartData['data']) ||
      lineChartData['data'].length == 0) {
    this.errorMsg = 'No data to display.';
    return;
  }

  var specs = lineChartData['data'].map(function(series) {
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
      xaxis: {
        mode: 'time',
        timeformat: '%y/%m/%d'
      },
      lines: {
        show: true
      },
      points: {
        show: true
      },
      zoom: {
        interactive: true
      },
      pan: {
        interactive: true
      },
      grid: {
        clickable: true,
        autohighlight: true
      }
    });
  }.bind(this));

  this.chartElement_.bind('plotclick', function(event, pos, obj) {
    if (obj) {
      var date = new Date(obj.datapoint[0]);
      this.hoverColor = obj.series.color;
      this.hoverText = 'On ' + date.toDateString() + ', there were ' +
                       obj.datapoint[1] + ' ' + obj.series.label + ' systems.';
    }
  }.bind(this));

  this.chartElement_.resize();
};

/**
 * ChartDirective definition.
 *
 * @return {angular.Directive} Directive definition object.
 */
exports.ChartDirective = function() {
  return {
    scope: {
      typedData: "="
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
exports.ChartDirective.directive_name = 'grrChart';
