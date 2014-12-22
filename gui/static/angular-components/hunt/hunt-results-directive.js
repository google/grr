'use strict';

goog.provide('grrUi.hunt.huntResultsDirective.HuntResultsController');
goog.provide('grrUi.hunt.huntResultsDirective.HuntResultsDirective');

goog.scope(function() {



/**
 * Controller for HuntResultsDirective.
 *
 * @constructor
 * @param {!angular.Scope} $scope
 * @ngInject
 */
grrUi.hunt.huntResultsDirective.HuntResultsController = function($scope) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @type {string} */
  this.scope_.huntUrn;

  /** @export {string} */
  this.resultsUrn;

  this.scope_.$watch('huntUrn', this.onHuntUrnChange.bind(this));
};

var HuntResultsController =
    grrUi.hunt.huntResultsDirective.HuntResultsController;


/**
 * Handles huntUrn attribute changes.
 *
 * @export
 */
HuntResultsController.prototype.onHuntUrnChange = function() {
  this.resultsUrn = this.scope_.huntUrn + '/Results';
};



/**
 * Directive for displaying results of a hunt with a given URN.
 *
 * @constructor
 * @ngInject
 * @export
 */
grrUi.hunt.huntResultsDirective.HuntResultsDirective = function() {
  return {
    scope: {
      huntUrn: '='
    },
    restrict: 'E',
    templateUrl: 'static/angular-components/hunt/hunt-results.html',
    controller: HuntResultsController,
    controllerAs: 'controller'
  };
};


/**
 * Directive's name in Angular.
 *
 * @const
 * @export
 */
grrUi.hunt.huntResultsDirective.HuntResultsDirective.directive_name =
    'grrHuntResults';

});  // goog.scope
