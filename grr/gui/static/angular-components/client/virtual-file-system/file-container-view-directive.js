'use strict';

goog.provide('grrUi.client.virtualFileSystem.fileContainerViewDirective.FileContainerViewController');
goog.provide('grrUi.client.virtualFileSystem.fileContainerViewDirective.FileContainerViewDirective');

goog.scope(function() {

/**
 * Controller for FileContainerViewDirective.
 *
 * @param {!angular.Scope} $scope
 * @param {!grrUi.routing.routingService.RoutingService} grrRoutingService
 * @constructor
 * @ngInject
 */
grrUi.client.virtualFileSystem.fileContainerViewDirective.FileContainerViewController = function(
    $scope, grrRoutingService) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @private {!grrUi.routing.routingService.RoutingService} */
  this.grrRoutingService_ = grrRoutingService;

  /** @type {string} */
  this.cliendId;

  /** @type {string} */
  this.path;

  /** @type {string} */
  this.query;

  this.grrRoutingService_.uiOnParamsChanged(this.scope_, ['clientId', 'path', 'query'],
      this.onParamsChange_.bind(this));
};
var FileContainerViewController =
    grrUi.client.virtualFileSystem.fileContainerViewDirective.FileContainerViewController;


/**
 * Handles changes to the state params.
 *
 * @param {Array} newValues The new value of the watched state params.
 * @param {Object=} opt_stateParams The new value of all state params.
 * @private
 */
FileContainerViewController.prototype.onParamsChange_ = function(newValues, opt_stateParams) {
  this.clientId = opt_stateParams['clientId'];
  this.path = opt_stateParams['path'];
  this.query = opt_stateParams['query'];

  grr.hash.container = this.path;
  grr.hash.query = this.query;
};

/**
 * FileContainerViewDirective definition.
 *
 * @return {angular.Directive} Directive definition object.
 */
grrUi.client.virtualFileSystem.fileContainerViewDirective.FileContainerViewDirective = function() {
  return {
    scope: {},
    restrict: 'E',
    templateUrl: '/static/angular-components/client/virtual-file-system/file-container-view.html',
    controller: FileContainerViewController,
    controllerAs: 'controller'
  };
};


/**
 * Name of the directive in Angular.
 *
 * @const
 * @export
 */
grrUi.client.virtualFileSystem.fileContainerViewDirective.FileContainerViewDirective.directive_name =
    'grrFileContainerView';

});  // goog.scope
