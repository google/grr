goog.module('grrUi.stats.chartDirective');
goog.module.declareLegacyNamespace();

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
  };
};


/**
 * Name of the directive in Angular.
 *
 * @const
 * @export
 */
exports.ChartDirective.directive_name = 'grrChart';
