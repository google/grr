'use strict';

goog.provide('grrUi.hunt.huntErrorsDirective.HuntErrorsController');
goog.provide('grrUi.hunt.huntErrorsDirective.HuntErrorsDirective');

goog.scope(function() {



/**
 * Controller for HuntErrorsDirective.
 *
 * @constructor
 * @param {!angular.Scope} $scope
 * @ngInject
 */
grrUi.hunt.huntErrorsDirective.HuntErrorsController = function($scope) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @type {string} */
  this.scope_.huntUrn;

  /** @export {string} */
  this.errorsUrl;

  this.scope_.$watch('huntUrn', this.onHuntUrnChange_.bind(this));
};

var HuntErrorsController = grrUi.hunt.huntErrorsDirective.HuntErrorsController;


/**
 * Handles huntUrn attribute changes.
 *
 * @private
 */
HuntErrorsController.prototype.onHuntUrnChange_ = function() {
  if (angular.isDefined(this.scope_.huntUrn)) {
    var huntUrnComponents = this.scope_.huntUrn.split('/');
    var huntId = huntUrnComponents[huntUrnComponents.length - 1];
    this.errorsUrl = 'hunts/' + huntId + '/errors';
  }
};


/**
 * Directive for displaying errors of a hunt with a given URN.
 *
 * @constructor
 * @ngInject
 * @export
 */
grrUi.hunt.huntErrorsDirective.HuntErrorsDirective = function() {
  return {
    scope: {
      huntUrn: '='
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
