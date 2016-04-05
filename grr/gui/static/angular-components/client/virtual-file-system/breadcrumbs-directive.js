'use strict';

goog.provide('grrUi.client.virtualFileSystem.breadcrumbsDirective.BreadcrumbsController');
goog.provide('grrUi.client.virtualFileSystem.breadcrumbsDirective.BreadcrumbsDirective');

goog.scope(function() {

/**
 * Controller for BreadcrumbsDirective.
 *
 * @constructor
 * @param {!angular.Scope} $rootScope
 * @param {!angular.Scope} $scope
 * @param {!grrUi.core.apiService.ApiService} grrApiService
 * @ngInject
 */
grrUi.client.virtualFileSystem.breadcrumbsDirective.BreadcrumbsController = function(
    $rootScope, $scope, grrApiService) {
  /** @private {!angular.Scope} */
  this.rootScope_ = $rootScope;

  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @type {Array}  */
  this.items;

  /** @type {string}  */
  this.activeItem;

  this.scope_.$watch('path', this.onPathChange_.bind(this));
};

var BreadcrumbsController =
    grrUi.client.virtualFileSystem.breadcrumbsDirective.BreadcrumbsController;

/**
 * Handles changes to the path.
 *
 * @private
 */
BreadcrumbsController.prototype.onPathChange_ = function() {
  if (this.scope_['path']) {
    var components = this.scope_['path'].split('/');

    var currentPath = '';
    this.items = [];
    angular.forEach(components.slice(0, -1), function(component) {
      currentPath +=  '/' + component;
      this.items.push({
        name: component,
        path: currentPath
      });
    }.bind(this));
    this.activeItem = components[components.length - 1];
  }
};

/**
 * Selects a path by calling the directive's callback method.
 *
 * @export
 */
BreadcrumbsController.prototype.selectPath = function(path) {
  var callback = this.scope_['onSelected'];
  if (callback) {
    callback({path: path.substring(1)}); // Remove leading slash.
  }
};

/**
 * BreadcrumbsDirective definition.
 * @return {angular.Directive} Directive definition object.
 */
grrUi.client.virtualFileSystem.breadcrumbsDirective.BreadcrumbsDirective = function() {
  return {
    restrict: 'E',
    scope: {
      path: '=',
      onSelected: '&'
    },
    templateUrl: '/static/angular-components/client/virtual-file-system/breadcrumbs.html',
    controller: BreadcrumbsController,
    controllerAs: 'controller'
  };
};


/**
 * Name of the directive in Angular.
 *
 * @const
 * @export
 */
grrUi.client.virtualFileSystem.breadcrumbsDirective.BreadcrumbsDirective.directive_name =
    'grrBreadcrumbs';

});  // goog.scope
