'use strict';

goog.provide('grrUi.client.virtualFileSystem.recursiveListButtonDirective.RecursiveListButtonController');
goog.provide('grrUi.client.virtualFileSystem.recursiveListButtonDirective.RecursiveListButtonDirective');

goog.require('grrUi.client.virtualFileSystem.utils.getFolderFromPath');


goog.scope(function() {


var getFolderFromPath = grrUi.client.virtualFileSystem.utils.getFolderFromPath;


/**
 * Controller for RecursiveListButtonDirective.
 *
 * @constructor
 * @param {!angular.Scope} $scope
 * @param {!angularUi.$modal} $modal Bootstrap UI modal service.
 * @param {!grrUi.core.apiService.ApiService} grrApiService
 * @param {!grrUi.core.reflectionService.ReflectionService} grrReflectionService
 * @ngInject
 */
grrUi.client.virtualFileSystem.recursiveListButtonDirective
    .RecursiveListButtonController = function(
    $scope, $modal, grrApiService, grrReflectionService) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @private {!angularUi.$modal} */
  this.modal_ = $modal;

  /** @private {!grrUi.core.apiService.ApiService} */
  this.grrApiService_ = grrApiService;

  /** @private {!grrUi.core.reflectionService.ReflectionService} */
  this.grrReflectionService_ = grrReflectionService;

  /** @type {?boolean} */
  this.requestSent;

  /** @type {?boolean} */
  this.done;

  /** @type {?string} */
  this.error;

  /** @type {Object} */
  this.refreshOperation;
};
var RecursiveListButtonController =
    grrUi.client.virtualFileSystem.recursiveListButtonDirective
    .RecursiveListButtonController;


/**
 * @const {number}
 */
RecursiveListButtonController.MAX_DEPTH = 5;


/**
 * Handles mouse clicks on itself.
 *
 * @export
 */
RecursiveListButtonController.prototype.onClick = function() {
  this.requestSent = false;
  this.done = false;
  this.error = null;

  this.grrReflectionService_.getRDFValueDescriptor(
      'ApiCreateVfsRefreshOperationArgs', true).then(function(descriptors) {
    this.refreshOperation = angular.copy(
        descriptors['ApiCreateVfsRefreshOperationArgs']['default']);

    var filePath = angular.copy(descriptors['RDFString']['default']);
    filePath['value'] = getFolderFromPath(this.scope_['filePath']);
    this.refreshOperation['value']['file_path'] = filePath;

    var maxDepth = angular.copy(descriptors['RDFInteger']['default']);
    maxDepth['value'] = RecursiveListButtonController.MAX_DEPTH;
    this.refreshOperation['value']['max_depth'] = maxDepth;

    this.refreshOperation['value']['notify_user'] = true;

    this.modal_.open({
      templateUrl: '/static/angular-components/client/virtual-file-system/' +
          'recursive-list-button-modal.html',
      scope: this.scope_
    });
  }.bind(this));
};


/**
 * Sends current settings value to the server and reloads the page after as
 * soon as server acknowledges the request afer a small delay. The delay is
 * needed so that the user can see the success message.
 *
 * @export
 */
RecursiveListButtonController.prototype.createRefreshOperation = function() {
  var aff4Prefix = 'aff4:/';
  var clientId = this.scope_['clientId'];
  if (clientId.toLowerCase().indexOf(aff4Prefix) == 0) {
    clientId = clientId.substr(aff4Prefix.length);
  }

  var url = 'clients/' + clientId + '/vfs-refresh-operations';
  this.grrApiService_.post(
      url, this.refreshOperation, true).then(
      function success() {
        this.done = true;
      }.bind(this),
      function failure(response) {
        this.done = true;
        this.error = response.data.message || 'Unknown error.';
        this.requestSent = false;
      }.bind(this));

  this.requestSent = true;
};

/**
 * RecursiveListButtonDirective renders a button that shows a dialog that allows
 * users to change their personal settings.
 *
 * @return {!angular.Directive} Directive definition object.
 */
grrUi.client.virtualFileSystem.recursiveListButtonDirective
    .RecursiveListButtonDirective = function() {
  return {
    scope: {
      clientId: '=',
      filePath: '='
    },
    restrict: 'E',
    templateUrl: '/static/angular-components/client/virtual-file-system/' +
        'recursive-list-button.html',
    controller: RecursiveListButtonController,
    controllerAs: 'controller'
  };
};


/**
 * Name of the directive in Angular.
 *
 * @const
 * @export
 */
grrUi.client.virtualFileSystem.recursiveListButtonDirective.RecursiveListButtonDirective
    .directive_name = 'grrRecursiveListButton';

});  // goog.scope
