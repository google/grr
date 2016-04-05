'use strict';

goog.provide('grrUi.core.resultsCollectionDirective.ResultsCollectionController');
goog.provide('grrUi.core.resultsCollectionDirective.ResultsCollectionDirective');
goog.require('grrUi.core.downloadCollectionFilesDirective.valuePointsToFile');

goog.scope(function() {



/**
 * Controller for ResultsCollectionDirective..
 *
 * @constructor
 * @ngInject
 */
grrUi.core.resultsCollectionDirective.ResultsCollectionController = function() {
  /** @type {boolean} */
  this.resultsAreFiles;
};
var ResultsCollectionController =
    grrUi.core.resultsCollectionDirective.ResultsCollectionController;


/**
 * Transformation callback for results table items provider that determines
 * whether results can be downloaded as an archive.
 *
 * @param {!Array<Object>} items Array of log items.
 * @return {!Array<Object>} Transformed items.
 * @export
 */
ResultsCollectionController.prototype.transformItems = function(items) {
  if (!angular.isDefined(this.resultsAreFiles)) {
    this.resultsAreFiles = items.length > 0 &&
        grrUi.core.downloadCollectionFilesDirective.valuePointsToFile(items[0]);
  }

  return items;
};


/**
 * Directive for displaying results collection via given URLs.
 *
 * @constructor
 * @ngInject
 * @export
 */
grrUi.core.resultsCollectionDirective.ResultsCollectionDirective = function() {
  return {
    scope: {
      resultsUrl: '=',
      outputPluginsUrl: '=',
      exportCommandUrl: '=?',
      downloadFilesUrl: '='
    },
    restrict: 'E',
    templateUrl: '/static/angular-components/core/results-collection.html',
    controller: ResultsCollectionController,
    controllerAs: 'controller'
  };
};


/**
 * Directive's name in Angular.
 *
 * @const
 * @export
 */
grrUi.core.resultsCollectionDirective.ResultsCollectionDirective
    .directive_name = 'grrResultsCollection';


});  // goog.scope
