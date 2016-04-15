'use strict';

goog.provide('grrUi.core.resultsCollectionDirective.ResultsCollectionController');
goog.provide('grrUi.core.resultsCollectionDirective.ResultsCollectionDirective');

goog.require('grrUi.core.fileDownloadUtils.getFileUrnFromValue');


goog.scope(function() {



/**
 * Controller for ResultsCollectionDirective..
 *
 * @constructor
 * @param {!angular.Scope} $scope
 * @ngInject
 */
grrUi.core.resultsCollectionDirective.ResultsCollectionController = function(
    $scope) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

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
        grrUi.core.fileDownloadUtils.getFileUrnFromValue(items[0]) != null;
  }

  if (this.scope_['transformItems']) {
    return this.scope_['transformItems']({'items': items});
  } else {
    return items;
  }
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
      downloadFilesUrl: '=',
      transformItems: '&?'
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
