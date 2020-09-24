goog.module('grrUi.hunt.huntErrorsDirective');
goog.module.declareLegacyNamespace();



/** @type {number} */
let AUTO_REFRESH_INTERVAL_MS = 20 * 1000;

/**
 * Sets the delay between automatic refreshes.
 *
 * @param {number} millis Interval value in milliseconds.
 * @export
 */
exports.setAutoRefreshInterval = function(millis) {
  AUTO_REFRESH_INTERVAL_MS = millis;
};


/**
 * Controller for HuntErrorsDirective.
 * @unrestricted
 */
const HuntErrorsController = class {
  /**
   * @param {!angular.Scope} $scope
   * @ngInject
   */
  constructor($scope) {
    /** @private {!angular.Scope} */
    this.scope_ = $scope;

    /** @type {string} */
    this.scope_.huntId;

    /** @export {string} */
    this.errorsUrl;

    /** @type {number} */
    this.autoRefreshInterval = AUTO_REFRESH_INTERVAL_MS;

    this.scope_.$watch('huntId', this.onHuntIdChange_.bind(this));
  }

  /**
   * Handles huntId attribute changes.
   *
   * @param {string} huntId
   * @private
   */
  onHuntIdChange_(huntId) {
    if (angular.isDefined(huntId)) {
      this.errorsUrl = 'hunts/' + huntId + '/errors';
    }
  }
};



/**
 * Directive for displaying errors of a hunt with a given URN.
 *
 * @return {!angular.Directive} Directive definition object.
 * @ngInject
 * @export
 */
exports.HuntErrorsDirective = function() {
  return {
    scope: {huntId: '='},
    restrict: 'E',
    templateUrl: '/static/angular-components/hunt/hunt-errors.html',
    controller: HuntErrorsController,
    controllerAs: 'controller'
  };
};


/**
 * Directive's name in Angular.
 *
 * @const
 * @export
 */
exports.HuntErrorsDirective.directive_name = 'grrHuntErrors';
