'use strict';

goog.provide('grrUi.semantic.statEntryDirective.StatEntryController');
goog.provide('grrUi.semantic.statEntryDirective.StatEntryDirective');

goog.require('grrUi.core.fileDownloadUtils.pathSpecToAff4Path');
goog.require('grrUi.core.serverErrorButtonDirective.ServerErrorButtonDirective');

goog.scope(function() {

var ERROR_EVENT_NAME = grrUi.core.serverErrorButtonDirective.ServerErrorButtonDirective.error_event_name;

var pathSpecToAff4Path = grrUi.core.fileDownloadUtils.pathSpecToAff4Path;

/**
 * Controller for StatEntryDirective.
 *
 * @param {!angular.Scope} $rootScope
 * @param {!angular.Scope} $scope
 * @param {!grrUi.core.apiService.ApiService} grrApiService
 * @constructor
 * @ngInject
 */
grrUi.semantic.statEntryDirective.StatEntryController = function(
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

var StatEntryController =
    grrUi.semantic.statEntryDirective.StatEntryController;


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
grrUi.semantic.statEntryDirective.StatEntryDirective = function() {
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
grrUi.semantic.statEntryDirective.StatEntryDirective.directive_name =
    'grrStatEntry';

/**
 * Semantic type corresponding to this directive.
 *
 * @const
 * @export
 */
grrUi.semantic.statEntryDirective.StatEntryDirective.semantic_types =
    ['StatEntry', '__DownloadableStatEntry'];


});  // goog.scope
