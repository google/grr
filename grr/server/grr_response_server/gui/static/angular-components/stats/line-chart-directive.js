goog.module('grrUi.stats.lineChartDirective');
goog.module.declareLegacyNamespace();

const {buildTimeseriesGraph} = goog.require('grrUi.stats.graphUtils');

/**
 * Controller for LineChartDirective.
 *
 * @param {!angular.Scope} $scope
 * @param {!angular.jQuery} $element
 * @constructor
 * @ngInject
 */
const LineChartController = function($scope, $element) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @private {!angular.jQuery} */
  this.element_ = $element;

  /** @private {!angular.jQuery} */
  this.chartElement_ = this.element_.find('.chart');

  /** @private {!angular.jQuery} */
  this.chartLegendElement_ = this.element_.find('.chart-legend');

  this.scope_.$watch('typedData', (typedData) => {
    if (angular.isDefined(typedData)) {
      this.initLineChart_(typedData['value']);
    }
  });
};


/**
 * Initializes an line chart.
 *
 * @param {!Object} lineChartData The data to be displayed, with type
 *                                annotations.
 * @private
 */
LineChartController.prototype.initLineChart_ = function(lineChartData) {
  if (angular.isUndefined(lineChartData['data']) ||
      lineChartData['data'].length == 0) {
    this.errorMsg = 'No data to display.';
    return;
  }

  const series = {};
  angular.forEach(lineChartData['data'], (serie) => {
    const label = serie['value']['label']['value'];
    series[label] = serie['value']['points'].map(
        p => [p['value']['x']['value'], p['value']['y']['value']]);
  });

  this.chartElement_.resize(() => {
    this.chartElement_.html('');
    buildTimeseriesGraph(this.chartElement_, this.chartLegendElement_, series);
  });
  this.chartElement_.resize();
};

/**
 * LineChartDirective definition.
 *
 * @return {!angular.Directive} Directive definition object.
 */
exports.LineChartDirective = function() {
  return {
    scope: {
      typedData: "="
    },
    restrict: 'E',
    templateUrl: '/static/angular-components/stats/line-chart.html',
    controller: LineChartController,
    controllerAs: 'controller'
  };
};


/**
 * Name of the directive in Angular.
 *
 * @const
 * @export
 */
exports.LineChartDirective.directive_name = 'grrLineChart';
