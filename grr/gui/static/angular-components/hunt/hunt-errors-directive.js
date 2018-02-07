'use strict';

goog.provide('grrUi.hunt.huntErrorsDirective');
goog.provide('grrUi.hunt.huntErrorsDirective.HuntErrorsDirective');

goog.scope(function() {


/** @const {number} */
grrUi.hunt.huntErrorsDirective.AUTO_REFRESH_INTERVAL_MS = 20 * 1000;


/**
 * Controller for HuntErrorsDirective.
 *
 * @constructor
 * @param {!angular.Scope} $scope
 * @ngInject
 */
const HuntErrorsController = function($scope) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @type {string} */
  this.scope_.huntId;

  /** @export {string} */
  this.errorsUrl;

  /** @type {number} */
  this.autoRefreshInterval =
      grrUi.hunt.huntErrorsDirective.AUTO_REFRESH_INTERVAL_MS;

  this.scope_.$watch('huntId', this.onHuntIdChange_.bind(this));
};



/**
 * Handles huntId attribute changes.
 *
 * @param {string} huntId
 * @private
 */
HuntErrorsController.prototype.onHuntIdChange_ = function(huntId) {
  if (angular.isDefined(huntId)) {
    this.errorsUrl = 'hunts/' + huntId + '/errors';
  }
};


/**
 * Directive for displaying errors of a hunt with a given URN.
 *
 * @return {!angular.Directive} Directive definition object.
 * @ngInject
 * @export
 */
grrUi.hunt.huntErrorsDirective.HuntErrorsDirective = function() {
  return {
    scope: {
      huntId: '='
    },
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
grrUi.hunt.huntErrorsDirective.HuntErrorsDirective.directive_name =
    'grrHuntErrors';

});  // goog.scope
