'use strict';

goog.provide('grrUi.core.forceRefreshDirective.ForceRefreshController');
goog.provide('grrUi.core.forceRefreshDirective.ForceRefreshDirective');

goog.scope(function() {

/**
 * Controller for force-refresh directive.
 *
 * @param {!angular.Scope} $scope
 * @constructor
 * @ngInject
 */
grrUi.core.forceRefreshDirective.ForceRefreshController = function($scope) {

  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @export {boolean} */
  this.show = true;

  this.scope_.$watch('refreshTrigger', function(newValue) {
    this.show = false;

    this.scope_.$evalAsync(function() {
      this.show = true;
    }.bind(this));
  }.bind(this), true);
};
var ForceRefreshController =
    grrUi.core.forceRefreshDirective.ForceRefreshController;

/**
 * Directive that displays RDFDatetime values.
 *
 * @constructor
 * @ngInject
 * @export
 */
grrUi.core.forceRefreshDirective.ForceRefreshDirective = function() {
  return {
    scope: {
      refreshTrigger: '=',
    },
    restrict: 'EA',
    transclude: true,
    template: '<div ng-if="controller.show"><ng-transclude /></div>',
    controller: ForceRefreshController,
    controllerAs: 'controller'
  };
};


/**
 * Directive's name in Angular.
 *
 * @const
 * @export
 */
grrUi.core.forceRefreshDirective.ForceRefreshDirective.directive_name =
    'grrForceRefresh';

});  // goog.scope
