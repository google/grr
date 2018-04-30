'use strict';

goog.module('grrUi.core.periodicRefreshDirective');
goog.module.declareLegacyNamespace();



/**
 * Controller for periodic-refresh directive.
 *
 * @param {!angular.Scope} $scope
 * @param {!angular.$interval} $interval
 * @constructor
 * @ngInject
 */
const PeriodicRefreshController = function(
    $scope, $interval) {

  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @private {!angular.$interval} */
  this.interval_ = $interval;

  /** @export {number} */
  this.refreshTrigger = 0;

  /** @private {angular.$q.Promise} */
  this.updateOperationInterval_;

  this.scope_.$watch('interval', this.onIntervalChange_.bind(this));

  this.scope_.$on('$destroy', function() {
    if (this.updateOperationInterval_) {
      this.interval_.cancel(this.updateOperationInterval_);
    }
  }.bind(this));
};


/**
 * @param {?} newValue
 * @private
 */
PeriodicRefreshController.prototype.onIntervalChange_ = function(newValue) {
  if (this.updateOperationInterval_) {
    this.interval_.cancel(this.updateOperationInterval_);
    this.updateOperationInterval_ = null;
  }

  if (angular.isDefined(newValue)) {
    this.updateOperationInterval_ = this.interval_(
        this.onInterval_.bind(this), newValue);
  }
};

/**
 * @private
 */
PeriodicRefreshController.prototype.onInterval_ = function() {
  this.refreshTrigger += 1;
  if (this.scope_['onRefresh']) {
    this.scope_['onRefresh']();
  }
};


/**
 * Directive that displays RDFDatetime values.
 *
 * @return {!angular.Directive} Directive definition object.
 * @ngInject
 * @export
 */
exports.PeriodicRefreshDirective = function() {
  return {
    scope: {
      interval: '=',
      onRefresh: '&'
    },
    restrict: 'EA',
    transclude: true,
    template: '<grr-force-refresh ' +
        'refresh-trigger="controller.refreshTrigger">' +
        '<ng-transclude /></grr-force-refresh>',
    controller: PeriodicRefreshController,
    controllerAs: 'controller'
  };
};


/**
 * Directive's name in Angular.
 *
 * @const
 * @export
 */
exports.PeriodicRefreshDirective.directive_name = 'grrPeriodicRefresh';
