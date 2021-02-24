goog.module('grrUi.client.clientLoadGraphSerieDirective');
goog.module.declareLegacyNamespace();



/**
 * Registers series in the graph.
 *
 * @return {!angular.Directive} Directive definition object.
 * @export
 */
exports.ClientLoadGraphSerieDirective = () => {
  return {
    scope: {
      clientId: '=',
      metric: '@',
      rate: '@',
      label: '@',
    },
    restrict: 'E',
    require: '^grrTimeseriesGraph',
    link: (scope, element, attrs, grrTimeseriesGraphCtrl) => {
      // Only register the graph when client id has a value.
      scope.$watch('::clientId', () => {
        if (angular.isUndefined(scope.clientId)) {
          return;
        }

        const options = {};
        if (scope.rate) {
          options['rate'] = scope.rate;
        }

        const path = `clients/${scope.clientId}/load-stats/${scope.metric}`;

        grrTimeseriesGraphCtrl.addSerieDescriptor({
          label: scope.label,
          requestPath: path,
          requestOptions: options
        });
      });
    }
  };
};


/**
 * Name of the directive as registered in Angular.
 *
 * @const
 * @export
 */
exports.ClientLoadGraphSerieDirective.directive_name =
    'grrClientLoadGraphSerie';
