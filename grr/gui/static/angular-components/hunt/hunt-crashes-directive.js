'use strict';

goog.provide('grrUi.hunt.huntCrashesDirective.HuntCrashesController');
goog.provide('grrUi.hunt.huntCrashesDirective.HuntCrashesDirective');

goog.scope(function() {



/**
 * Controller for HuntCrashesDirective.
 *
 * @constructor
 * @param {!angular.Scope} $scope
 * @ngInject
 */
grrUi.hunt.huntCrashesDirective.HuntCrashesController = function($scope) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @type {string} */
  this.scope_.huntUrn;

  /** @export {string} */
  this.crashesUrl;

  this.scope_.$watch('huntUrn', this.onHuntUrnChange_.bind(this));
};

var HuntCrashesController =
    grrUi.hunt.huntCrashesDirective.HuntCrashesController;


/**
 * Handles huntUrn attribute changes.
 *
 * @private
 */
HuntCrashesController.prototype.onHuntUrnChange_ = function() {
  if (angular.isDefined(this.scope_.huntUrn)) {
    var huntUrnComponents = this.scope_.huntUrn.split('/');
    var huntId = huntUrnComponents[huntUrnComponents.length - 1];
    this.crashesUrl = 'hunts/' + huntId + '/crashes';
  }
};


/**
 * Directive for displaying crashes of a hunt with a given URN.
 *
 * @constructor
 * @ngInject
 * @export
 */
grrUi.hunt.huntCrashesDirective.HuntCrashesDirective = function() {
  return {
    scope: {
      huntUrn: '='
    },
    restrict: 'E',
    templateUrl: '/static/angular-components/hunt/hunt-crashes.html',
    controller: HuntCrashesController,
    controllerAs: 'controller'
  };
};


/**
 * Directive's name in Angular.
 *
 * @const
 * @export
 */
grrUi.hunt.huntCrashesDirective.HuntCrashesDirective.directive_name =
    'grrHuntCrashes';

});  // goog.scope
