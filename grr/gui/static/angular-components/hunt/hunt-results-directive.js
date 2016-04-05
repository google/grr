'use strict';

goog.provide('grrUi.hunt.huntResultsDirective.HuntResultsController');
goog.provide('grrUi.hunt.huntResultsDirective.HuntResultsDirective');
goog.require('grrUi.core.downloadCollectionFilesDirective.valuePointsToFile');

goog.scope(function() {



/**
 * Controller for HuntResultsDirective.
 *
 * @constructor
 * @param {!angular.Scope} $scope
 * @ngInject
 */
grrUi.hunt.huntResultsDirective.HuntResultsController = function(
    $scope) {
  /** @export {string} */
  this.resultsUrl;

  /** @export {string} */
  this.outputPluginsUrl;

  /** @export {string} */
  this.downloadFilesUrl;

  $scope.$watch('huntUrn', this.onHuntUrnChange.bind(this));
};
var HuntResultsController =
    grrUi.hunt.huntResultsDirective.HuntResultsController;


/**
 * Handles huntUrn attribute changes.
 *
 * @param {?string} huntUrn
 * @export
 */
HuntResultsController.prototype.onHuntUrnChange = function(huntUrn) {
  if (!angular.isString(huntUrn)) {
    return;
  }

  var components = huntUrn.split('/');
  var huntId = components[components.length - 1];

  this.resultsUrl = '/hunts/' + huntId + '/results';
  this.downloadFilesUrl = this.resultsUrl + '/files-archive';
  this.outputPluginsUrl = '/hunts/' + huntId + '/output-plugins';
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
    templateUrl: '/static/angular-components/hunt/hunt-results.html',
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
