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

  /** @export {Object.<string, Object>} */
  this.queryParameters;

  /** @export {boolean} */
  this.hasQueryParameters;

  this.scope_.$watch('::value', this.onValueChange.bind(this));
};

var ApiRouteController =
    grrUi.docs.apiRouteDirective.ApiRouteController;


/**
 * Handles value attribute changes.
 *
 * @export
 */
ApiRouteController.prototype.onValueChange = function() {
  var routeComponents = this.routeComponents = [];
  var queryParameters = this.queryParameters = {};

  if (angular.isString(this.scope_.value)) {
    var route = this.scope_.value;

    var questionMarkIndex = route.indexOf('?');
    if (questionMarkIndex != -1) {
      var queryParamString = route.substring(questionMarkIndex + 1,
                                             route.length);
      route = route.substring(0, questionMarkIndex);

      var vars = queryParamString.split('&');
      angular.forEach(vars, function(variable) {
        var pair = variable.split('=');
        if (pair.length == 2) {
          queryParameters[pair[0]] = pair[1];
        } else {
          queryParameters[pair[0]] = null;
        }
      });
    }

    var components = route.split('/');
    angular.forEach(components, function(component) {
      if (component.length > 0) {
        if (component[0] === '<') {
          component = component.substring(1, component.length - 1);
          var componentParts = component.split(':');
          var componentType, componentValue;
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
grrUi.docs.apiRouteDirective.ApiRouteDirective.directive_name =
    'grrApiRoute';


});  // goog.scope
