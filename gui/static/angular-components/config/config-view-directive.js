'use strict';

goog.provide('grrUi.config.configViewDirective.ConfigViewController');
goog.provide('grrUi.config.configViewDirective.ConfigViewDirective');

goog.scope(function() {

var directive = grrUi.config.configViewDirective;



/**
 * Controller for ConfigViewDirective.
 *
 * @constructor
 * @param {!angular.Scope} $scope
 * @param {!angular.$http} $http Angular HTTP service.
 * @ngInject
 */
directive.ConfigViewController = function($scope, $http) {
  var ctrl = this;

  $http.get('/api/config').success(function(items) {
    ctrl.items = items;
  });
};
var ConfigViewController = directive.ConfigViewController;


/**
 * ConfigViewDirective definition.
 * @return {angular.Directive} Directive definition object.
 */
directive.ConfigViewDirective = function() {
  return {
    restrict: 'E',
    scope: {},
    templateUrl: '/static/angular-components/config/config-view.html',
    controller: ConfigViewController,
    controllerAs: 'ctrl'
  };
};


/**
 * Name of the directive in Angular.
 *
 * @const
 * @export
 */
grrUi.config.configViewDirective.ConfigViewDirective.directive_name =
    'grrConfigView';

});  // goog.scope
