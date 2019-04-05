goog.module('grrUi.stats.comparisonChartDirective');
goog.module.declareLegacyNamespace();

/**
 * Controller for ComparisonChartDirective.
 *
 * @param {!angular.Scope} $scope
 * @constructor
 * @ngInject
 */
const ComparisonChartController = function($scope) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  this.values = [];

  this.scope_.$watchGroup(
      ['typedData', 'preserveOrder'],
      ([typedData, _]) => {
        if (angular.isDefined(typedData)) {
          this.initComparisonChart_(typedData['value']);
        }
      });
};

/**
 * Initializes a comparison chart.
 *
 * @param {!Object} comparisonChartData The data to be displayed, with type
 *                                      annotations.
 * @private
 */
ComparisonChartController.prototype.initComparisonChart_ = function(
    comparisonChartData) {
  this.values = [];

  let maxValue = 0;
  comparisonChartData['data'].forEach((series) => {
    const label = series['value']['label']['value'];
    const value = series['value']['x']['value'];
    this.values.push({label: label, value: value});

    if (value > maxValue) {
      maxValue = value;
    }
  });

  if (!this.scope_['preserveOrder']) {
    this.values.sort((a, b) => b['value'] - a['value']);
  }
  angular.forEach(this.values, (v) => {
    v['percent'] = Math.round(v['value'] / maxValue * 100);
  });
};


/**
 * ComparisonChartDirective definition.
 *
 * @return {!angular.Directive} Directive definition object.
 */
exports.ComparisonChartDirective = function() {
  return {
    scope: {typedData: '=', preserveOrder: '='},
    restrict: 'E',
    templateUrl: '/static/angular-components/stats/comparison-chart.html',
    controller: ComparisonChartController,
    controllerAs: 'controller'
  };
};


/**
 * Name of the directive in Angular.
 *
 * @const
 * @export
 */
exports.ComparisonChartDirective.directive_name = 'grrComparisonChart';
