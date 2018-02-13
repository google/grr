'use strict';

goog.module('grrUi.semantic.statEntryDirective');
goog.module.declareLegacyNamespace();

const {ServerErrorButtonDirective} = goog.require('grrUi.core.serverErrorButtonDirective');
const {pathSpecToAff4Path} = goog.require('grrUi.core.fileDownloadUtils');


var ERROR_EVENT_NAME = ServerErrorButtonDirective.error_event_name;



/**
 * Controller for StatEntryDirective.
 *
 * @param {!angular.Scope} $rootScope
 * @param {!angular.Scope} $scope
 * @param {!grrUi.core.apiService.ApiService} grrApiService
 * @constructor
 * @ngInject
 */
const StatEntryController = function(
    $rootScope, $scope, grrApiService) {
  /** @private {!angular.Scope} */
  this.rootScope_ = $rootScope;

  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @private {!grrUi.core.apiService.ApiService} */
  this.grrApiService_ = grrApiService;

  /** @type {string} */
  this.clientId;

  /** @type {Object} */
  this.aff4Path;

  /** @type {Object} */
  this.statEntry;

  /** @type {string} */
  this.downloadUrl;

  /** @type {Object} */
  this.downloadParams;

  this.scope_.$watch('::value', this.onValueChange_.bind(this));
};



/**
 * Handles changes of scope.value attribute.
 *
 * @param {Object} newValue StatEntry or __DownloadableStatEntry value.
 * @private
 */
StatEntryController.prototype.onValueChange_ = function(newValue) {
  if (angular.isUndefined(newValue)) {
    return;
  }

  if (newValue['type'] == '__DownloadableStatEntry') {
    this.statEntry = newValue['originalValue'];
    this.downloadUrl = newValue['downloadUrl'];
    this.downloadParams = newValue['downloadParams'];
  } else {
    this.statEntry = newValue;
  }

  if (this.clientId && angular.isDefined(this.statEntry['value']['pathspec'])) {
    this.aff4Path = {
      type: 'RDFURN',
      value: pathSpecToAff4Path(this.statEntry['value']['pathspec'], this.clientId)
    };
  } else {
    this.aff4Path = {
      type: 'RDFString',
      value: '<unknown>'
    };
  }
};


/**
 * Handler for the download click events.
 */
StatEntryController.prototype.onDownloadClick = function() {
  this.grrApiService_.downloadFile(this.downloadUrl, this.downloadParams).then(
      function success() {}.bind(this),
      function failure(response) {
        if (response.status !== 500) {
          this.rootScope_.$broadcast(
              ERROR_EVENT_NAME, {
                message: 'Couldn\'t download the file. Most likely ' +
                    'it was just referenced and not downloaded from the ' +
                    'client.'
              });
        }
      }.bind(this));
};


/**
 * Directive that displays AFF4 object label.
 *
 * @return {angular.Directive} Directive definition object.
 * @export
 */
exports.StatEntryDirective = function() {
  return {
    scope: {
      value: '='
    },
    require: '?^grrClientContext',
    restrict: 'E',
    templateUrl: '/static/angular-components/semantic/stat-entry.html',
    controller: StatEntryController,
    controllerAs: 'controller',
    link: function(scope, element, attrs, grrClientContextCtrl) {
      if (grrClientContextCtrl) {
        scope['controller'].clientId = grrClientContextCtrl.clientId;
      }
    }
  };
};


/**
 * Name of the directive in Angular.
 */
exports.StatEntryDirective.directive_name = 'grrStatEntry';

/**
 * Semantic type corresponding to this directive.
 *
 * @const
 * @export
 */
exports.StatEntryDirective.semantic_types =
    ['StatEntry', '__DownloadableStatEntry'];
