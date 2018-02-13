'use strict';

goog.module('grrUi.core.resultsCollectionDirective');
goog.module.declareLegacyNamespace();

const {getPathSpecFromValue} = goog.require('grrUi.core.fileDownloadUtils');



/** @type {number} */
let AUTO_REFRESH_INTERVAL_MS = 20 * 1000;

/**
 * Sets the delay between automatic refreshes of the results collection.
 *
 * @param {number} millis Interval value in milliseconds.
 * @export
 */
exports.setAutoRefreshInterval = function(millis) {
  AUTO_REFRESH_INTERVAL_MS = millis;
};


/** @const {number} */
var MAX_ITEMS_TO_CHECK_FOR_FILES = 50;


/**
 * Controller for ResultsCollectionDirective..
 *
 * @constructor
 * @param {!angular.Scope} $scope
 * @ngInject
 */
const ResultsCollectionController = function(
    $scope) {

  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @type {boolean} */
  this.resultsArePresent;

  /** @type {boolean} */
  this.resultsAreFiles;

  /** @type {number} */
  this.autoRefreshInterval = AUTO_REFRESH_INTERVAL_MS;

  /** @private {number} */
  this.numCheckedItems_ = 0;
};

/**
 * Transformation callback for results table items provider that determines
 * whether results can be downloaded as an archive.
 *
 * @param {!Array<Object>} items Array of log items.
 * @return {!Array<Object>} Transformed items.
 * @export
 */
ResultsCollectionController.prototype.transformItems = function(items) {
  if (items.length > 0) {
    this.resultsArePresent = true;
  }

  if (!this.resultsAreFiles &&
      this.numCheckedItems_ < MAX_ITEMS_TO_CHECK_FOR_FILES) {
    this.numCheckedItems_ += items.length;

    this.resultsAreFiles = false;
    for (var i = 0; i < items.length; i++) {
      if (getPathSpecFromValue(items[i]) != null) {
        this.resultsAreFiles = true;
        break;
      }
    }
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
 * @return {!angular.Directive} Directive definition object.
 * @ngInject
 * @export
 */
exports.ResultsCollectionDirective = function() {
  return {
    scope: {
      resultsUrl: '=',
      exportedResultsUrl: '=',
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
exports.ResultsCollectionDirective.directive_name = 'grrResultsCollection';
