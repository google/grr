'use strict';

goog.provide('grrUi.core.downloadCollectionFilesDirective.DownloadCollectionFilesController');
goog.provide('grrUi.core.downloadCollectionFilesDirective.DownloadCollectionFilesDirective');
goog.provide('grrUi.core.downloadCollectionFilesDirective.valuePointsToFile');

goog.scope(function() {


/**
 * Returns true if given typed value points to a file.
 *
 * @param {Object} value Typed value.
 * @return {boolean} True if value points to a file, false otherwise.
 * @export
 */
grrUi.core.downloadCollectionFilesDirective.valuePointsToFile = function(
    value) {
  if (value['type'] == 'ApiFlowResult' || value['type'] == 'ApiHuntResult') {
    value = value['value']['payload'];
  }

  if (value['type'] == 'StatEntry' ||
      value['type'] == 'FileFinderResult' ||
      value['type'] == 'ArtifactFilesDownloaderResult') {
    return true;
  } else {
    return false;
  }
};


/**
 * Controller for DownloadCollectionFilesDirective.
 *
 * @constructor
 * @param {!angular.Scope} $scope
 * @param {!angular.$window} $window
 * @param {!grrUi.core.apiService.ApiService} grrApiService
 * @ngInject
 */
grrUi.core.downloadCollectionFilesDirective.DownloadCollectionFilesController =
    function($scope, $window, grrApiService) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @private {!grrUi.core.apiService.ApiService} */
  this.grrApiService_ = grrApiService;

  /** @type {string} */
  this.scope_.downloadUrl;

  /** @export {string} */
  this.primaryArchiveExtension;

  /** @export {string} */
  this.secondaryArchiveExtension;

  /** @export {boolean} */
  this.fileArchiveGenerationStarted;

  /** @export {boolean} */
  this.fileArchiveGenerationSuccess;

  /** @export {string} */
  this.fileArchiveGenerationError;

  /** @export {string} */
  this.exportCommand;

  if ($window.navigator.appVersion.indexOf('Mac') != -1) {
    this.primaryArchiveExtension = 'tar.gz';
    this.secondaryArchiveExtension = 'zip';
  } else {
    this.primaryArchiveExtension = 'zip';
    this.secondaryArchiveExtension = 'tar.gz';
  }

  this.scope_.$watch('exportCommandUrl', function(newValue) {
    if (angular.isUndefined(newValue)) {
      return;
    }

    this.grrApiService_.get(newValue).then(function(response) {
      if (angular.isDefined(response['data']['command'])) {
          this.exportCommand = response['data']['command'];
      }
    }.bind(this));
  }.bind(this));
};
var DownloadCollectionFilesController =
    grrUi.core.downloadCollectionFilesDirective
    .DownloadCollectionFilesController;


/**
 * Issue a request to generate archive with collection files.
 *
 * @param {string} format Archive format: either 'zip' or 'tar.gz'.
 * @export
 */
DownloadCollectionFilesController.prototype.generateFileArchive = function(
    format) {
  var requestFormat = format.toUpperCase().replace('.', '_');
  this.grrApiService_.downloadFile(
      this.scope_['downloadUrl'], {archive_format: requestFormat}).then(
          function success() {
            this.fileArchiveGenerationSuccess = true;
          }.bind(this),
          function failure(response) {
            this.fileArchiveGenerationError = response.data['message'];
          }.bind(this));

  this.fileArchiveGenerationStarted = true;
};


/**
 * Directive for displaying "download files referenced by collection" panel.
 *
 * @constructor
 * @ngInject
 * @export
 */
grrUi.core.downloadCollectionFilesDirective.DownloadCollectionFilesDirective =
    function() {
  return {
    scope: {
      exportCommandUrl: '=?',
      downloadUrl: '='
    },
    restrict: 'E',
    templateUrl: '/static/angular-components/core/' +
        'download-collection-files.html',
    controller: DownloadCollectionFilesController,
    controllerAs: 'controller'
  };
};


/**
 * Directive's name in Angular.
 *
 * @const
 * @export
 */
grrUi.core.downloadCollectionFilesDirective
    .DownloadCollectionFilesDirective
    .directive_name = 'grrDownloadCollectionFiles';

});  // goog.scope
