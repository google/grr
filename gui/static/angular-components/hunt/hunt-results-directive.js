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
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @type {string} */
  this.scope_.huntUrn;

  /** @export {string} */
  this.resultsUrn;

  /** @export {string} */
  this.downloadFilesUrl;

  /** @export {string} */
  this.outputPluginsMetadataUrn;

  /** @export {boolean} */
  this.resultsAreFiles;

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
  this.outputPluginsMetadataUrn = this.scope_.huntUrn + '/ResultsMetadata';

  var components = this.scope_.huntUrn.split('/');
  var huntId = components[components.length - 1];
  this.downloadFilesUrl = '/hunts/' + huntId + '/results/archive-files';
};


/**
 * Transformation callback for results table items provider that determines
 * whether results can be downloaded as an archive.
 *
 * @param {!Array<Object>} items Array of log items.
 * @return {!Array<Object>} Transformed items.
 * @export
 */
HuntResultsController.prototype.transformItems = function(items) {
  if (!angular.isDefined(this.resultsAreFiles)) {
    this.resultsAreFiles = items.length > 0 &&
        grrUi.core.downloadCollectionFilesDirective.valuePointsToFile(items[0]);
  }

  return items;
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
