goog.module('grrUi.docs.apiRouteDirective');
goog.module.declareLegacyNamespace();



/**
 * @typedef {{
 *             type:string,
 *             value:string
 *           }}
 */
let RouteComponent;



/**
 * Controller for ApiRouteDirective.
 * @unrestricted
 */
const ApiRouteController = class {
  /**
   * @param {!angular.Scope} $scope
   * @ngInject
   */
  constructor($scope) {
    /** @private {!angular.Scope} */
    this.scope_ = $scope;

    /** @export {Array.<RouteComponent>} */
    this.routeComponents;

    /** @export {Object.<string, Object>} */
    this.queryParameters;

    /** @export {boolean} */
    this.hasQueryParameters;

    this.scope_.$watch('::value', this.onValueChange.bind(this));
  }

  /**
   * Handles value attribute changes.
   *
   * @export
   */
  onValueChange() {
    const routeComponents = this.routeComponents = [];
    const queryParameters = this.queryParameters = {};

    if (angular.isString(this.scope_.value)) {
      let route = this.scope_.value;

      const questionMarkIndex = route.indexOf('?');
      if (questionMarkIndex != -1) {
        const queryParamString =
            route.substring(questionMarkIndex + 1, route.length);
        route = route.substring(0, questionMarkIndex);

        const vars = queryParamString.split('&');
        angular.forEach(vars, function(variable) {
          const pair = variable.split('=');
          if (pair.length == 2) {
            queryParameters[pair[0]] = pair[1];
          } else {
            queryParameters[pair[0]] = null;
          }
        });
      }

      const components = route.split('/');
      angular.forEach(components, function(component) {
        if (component.length > 0) {
          if (component[0] === '<') {
            component = component.substring(1, component.length - 1);
            const componentParts = component.split(':');
            let componentType;
            let componentValue;
            if (componentParts.length === 1) {
              componentType = 'string';
              componentValue = componentParts[0];
            } else {
              componentType = componentParts[0];
              componentValue = componentParts[1];
            }

            routeComponents.push({type: componentType, value: componentValue});
          } else {
            routeComponents.push({value: component});
          }
        }
      }.bind(this));
    }

    this.hasQueryParameters = Object.keys(queryParameters).length > 0;
  }
};



/**
 * Directive for displaying API route.
 *
 * @return {!angular.Directive} Directive definition object.
 * @ngInject
 * @export
 */
exports.ApiRouteDirective = function() {
  return {
    scope: {value: '='},
    restrict: 'E',
    templateUrl: '/static/angular-components/docs/api-route.html',
    controller: ApiRouteController,
    controllerAs: 'controller'
  };
};


/**
 * Directive's name in Angular.
 *
 * @const
 * @export
 */
exports.ApiRouteDirective.directive_name = 'grrApiRoute';
