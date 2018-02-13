'use strict';

goog.module('grrUi.core.downloadCollectionAsDirective');
goog.module.declareLegacyNamespace();

const {ServerErrorButtonDirective} = goog.require('grrUi.core.serverErrorButtonDirective');



var ERROR_EVENT_NAME = ServerErrorButtonDirective.error_event_name;


/**
 * Controller for DownloadCollectionAsDirective.
 *
 * @constructor
 * @param {!angular.Scope} $rootScope
 * @param {!angular.Scope} $scope
 * @param {!grrUi.core.apiService.ApiService} grrApiService
 * @ngInject
 */
const DownloadCollectionAsController = function(
    $rootScope, $scope, grrApiService) {
  /** @private {!angular.Scope} */
  this.rootScope_ = $rootScope;

  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @private {!grrUi.core.apiService.ApiService} */
  this.grrApiService_ = grrApiService;

  /** @type {Object} */
  this.pluginToDisplayName = {
    'csv-zip': 'CSV (Zipped)',
    'flattened-yaml-zip': 'Flattened YAML (Zipped)',
    'sqlite-zip': 'SQLite Scripts (Zipped)'
  };

  /** @type {string} */
  this.selectedPlugin = 'csv-zip';
};


/**
 * Handles clicks on "download as" buttons.
 *
 * @param {string} pluginName Name of the plugin to use for export.
 * @export
 */
DownloadCollectionAsController.prototype.downloadAs = function(pluginName) {
  var url = this.scope_['baseUrl'] + '/' + pluginName;
  this.grrApiService_.downloadFile(url).then(
      function success() {}.bind(this),
      function failure(response) {
        if (angular.isUndefined(response.status)) {
          this.rootScope_.$broadcast(
              ERROR_EVENT_NAME, {
                message: 'Couldn\'t download exported results.'
              });
        }
      }.bind(this)
  );
};


/**
 * Directive that displays results collection via given URLs.
 *
 * @ngInject
 * @export
 * @return {!angular.Directive} Directive definition object.
 */
exports.DownloadCollectionAsDirective = function() {
  return {
    scope: {
      baseUrl: '=',
    },
    restrict: 'E',
    templateUrl: '/static/angular-components/core/download-collection-as.html',
    controller: DownloadCollectionAsController,
    controllerAs: 'controller'
  };
};


/**
 * Directive's name in Angular.
 *
 * @const
 * @export
 */
exports.DownloadCollectionAsDirective.directive_name =
    'grrDownloadCollectionAs';
