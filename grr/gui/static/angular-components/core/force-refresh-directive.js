'use strict';

goog.module('grrUi.core.forceRefreshDirective');
goog.module.declareLegacyNamespace();



/**
 * Controller for force-refresh directive.
 *
 * @param {!angular.Scope} $scope
 * @param {!angular.jQuery} $element
 * @param {function(function(angular.jQuery, angular.Scope))} $transclude
 * @constructor
 * @ngInject
 */
const ForceRefreshController = function(
    $scope, $element, $transclude) {

  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @private {!angular.jQuery} */
  this.element_ = $element;

  /** @private {function(function(angular.jQuery, angular.Scope))} */
  this.transclude_ = $transclude;

  /** @private {angular.Scope|undefined} */
  this.transcludedScope_;

  this.scope_.$watch('refreshTrigger',
                     this.updateDom_.bind(this),
                     true);
};


/**
 * @private
 */
ForceRefreshController.prototype.updateDom_ = function() {
  if (angular.isDefined(this.transcludedScope_)) {
    this.transcludedScope_.$destroy();
    this.transcludedScope_ = undefined;
  }

  this.element_.empty();

  this.transclude_(function(clone, scope) {
    this.element_.empty();
    this.element_.append(clone);

    this.transcludedScope_ = scope;
  }.bind(this));
};


/**
 * Directive that displays RDFDatetime values.
 *
 * @return {!angular.Directive} Directive definition object.
 * @ngInject
 * @export
 */
exports.ForceRefreshDirective = function() {
  return {
    scope: {
      refreshTrigger: '=',
    },
    restrict: 'EA',
    transclude: true,
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
exports.ForceRefreshDirective.directive_name = 'grrForceRefresh';
