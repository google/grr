'use strict';

goog.module('grrUi.client.virtualFileSystem.breadcrumbsDirective');
goog.module.declareLegacyNamespace();



/**
 * Controller for BreadcrumbsDirective.
 *
 * @constructor
 * @param {!angular.Scope} $rootScope
 * @param {!angular.Scope} $scope
 * @param {!grrUi.core.apiService.ApiService} grrApiService
 * @ngInject
 */
const BreadcrumbsController = function(
    $rootScope, $scope, grrApiService) {
  /** @private {!angular.Scope} */
  this.rootScope_ = $rootScope;

  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @type {Array}  */
  this.items;

  /** @type {string|undefined}  */
  this.activeItem;

  this.scope_.$watchGroup(['path', 'stripEndingSlash'],
                          this.onDirectiveArgsChange_.bind(this));
};


/**
 * Handles changes to the directive arguments.
 *
 * On every change it rebuilds a list of components to be rendered in the
 * template.
 *
 * @private
 */
BreadcrumbsController.prototype.onDirectiveArgsChange_ = function() {
  var pathArg = this.scope_['path'];
  var stripEndingSlashArg = this.scope_['stripEndingSlash'];

  this.items = [];
  this.activeItem = undefined;
  if (!pathArg) {
    return;
  }

  var components = pathArg.split('/');
  if (stripEndingSlashArg && pathArg.endsWith('/')) {
    components = components.slice(0, components.length - 1);
  }

  // "path" argument is supposed to point to a currently selected file and
  // grr-breadcrumbs displays all the containing folders. So the last component
  // is supposed to be neglected as it's the filename of the actual file, when
  // we only care about the containing directories. Therefore having 1 or 0
  // components means invalid input and we display nothing.
  if (components.length < 2) {
    return;
  }
  components = components.slice(0, -1);

  var currentPath = '';
  angular.forEach(components.slice(0, -1), function(component) {
    currentPath +=  component + '/';
    this.items.push({
      name: component,
      path: currentPath
    });
  }.bind(this));
  this.activeItem = components[components.length - 1];
};

/**
 * Selects a path by assigning it to the scope..
 *
 * @export
 */
BreadcrumbsController.prototype.selectPath = function(path) {
  this.scope_['path'] = path;
};

/**
 * BreadcrumbsDirective definition. It displays containing directories
 * breadcrumbs for a currently selected file.
 *
 * @return {angular.Directive} Directive definition object.
 */
exports.BreadcrumbsDirective = function() {
  return {
    restrict: 'E',
    scope: {
      // "path" arguments is supposed to point to a currently selected file and
      // grr-breadcrumbs displays all the containing folders.
      path: '=',
      // If true, any trailing slash in "path" will be stripped. Useful when
      // "path" may point to a folder (i.e. "foo/bar/folder/"), but we want to
      // treat selected folders and files in the same way (i.e. for
      // "foo/bar/folder" we want "foo > bar" breadcrumbs).
      stripEndingSlash: '='
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
exports.BreadcrumbsDirective.directive_name = 'grrBreadcrumbs';
