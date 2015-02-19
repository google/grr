'use strict';

goog.provide('grrUi.docs.apiRouteDirective.ApiRouteController');
goog.provide('grrUi.docs.apiRouteDirective.ApiRouteDirective');
goog.provide('grrUi.docs.apiRouteDirective.RouteComponent');

goog.scope(function() {


/** @typedef {{
 *             type:string,
 *             value:string
 *           }}
 */
grrUi.docs.apiRouteDirective.RouteComponent;



/**
 * Controller for ApiRouteDirective.
 *
 * @constructor
 * @param {!angular.Scope} $scope
 * @ngInject
 */
grrUi.docs.apiRouteDirective.ApiRouteController = function($scope) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @export {Array.<grrUi.docs.apiRouteDirective.RouteComponent>} */
  this.routeComponents;

  this.scope_.$watch('value', this.onValueChange.bind(this));
};

var ApiRouteController =
    grrUi.docs.apiRouteDirective.ApiRouteController;


/**
 * Handles value attribute changes.
 *
 * @param {string} newValue New route value.
 * @export
 */
ApiRouteController.prototype.onValueChange = function(newValue) {
  var routeComponents = this.routeComponents = [];

  if (angular.isString(newValue)) {
    var components = newValue.split('/');
    angular.forEach(components, function(component) {
      if (component.length > 0) {
        if (component[0] === '<') {
          component = component.substring(1, component.length - 1);
          var componentParts = component.split(':');
          var componentType;
          if (componentParts.length === 1) {
            componentType = 'string';
          } else {
            componentType = componentParts[0];
          }
          routeComponents.push({type: componentType, value: component});
        } else {
          routeComponents.push({value: component});
        }
      }
    });
  }
};



/**
 * Directive for displaying API route.
 *
 * @constructor
 * @ngInject
 * @export
 */
grrUi.docs.apiRouteDirective.ApiRouteDirective = function() {
  return {
    scope: {
      value: '='
    },
    restrict: 'E',
    templateUrl: 'static/angular-components/docs/api-route.html',
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
grrUi.docs.apiRouteDirective.ApiRouteDirective.directive_name =
    'grrApiRoute';


});  // goog.scope
