'use strict';

goog.module('grrUi.client.virtualFileSystem.fileViewDirective');
goog.module.declareLegacyNamespace();


/**
 * Replaces all non-alphanumeric characters with their hex representation.
 *
 * @param {string} item
 * @return {string} A string with invalid chars replaced by their hex charcode
 *     value.
 * @private
 */
const replaceInvalidChars_ = function(item) {
  return item.replace(/[^a-zA-Z0-9]/g, function(invChar){
    var hex = invChar.charCodeAt(0).toString(16);
    return '_' + hex.toUpperCase();
  });
};


/**
 * Converts given filePath to a fileId.
 *
 * @param {string} filePath The path to a file.
 * @return {string} A unique id for the file derived from the path.
 * @export
 */
exports.getFileId = function(filePath) {
  var components = filePath.split('/');
  var result = components.map(replaceInvalidChars_);
  return '_' + result.join('-');
};


/**
 * Converts given id to a file path. This function is the opposite of getFileId.
 *
 * @param {string} fileId The file id.
 * @return {string} File path.
 * @export
 */
exports.getFilePathFromId = function(fileId) {
  var replaceEncodedChars = function(item) {
    return item.replace(/_[0-9A-F][0-9A-F]?/g, function(encChar) {
      var charNum = parseInt(encChar.substr(1), 16);
      return String.fromCharCode(charNum);
    });
  };

  // substr accounts for a leading '_'.
  var components = fileId.substr(1).split('-');
  var mapped = components.map(replaceEncodedChars);
  return mapped.join('/');
};


/**
 * Controller for FileViewDirective.
 *
 * @constructor
 * @param {!angular.Scope} $scope
 * @param {!grrUi.routing.routingService.RoutingService} grrRoutingService
 * @ngInject
 */
const FileViewController = function(
    $scope, grrRoutingService) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @private {!grrUi.routing.routingService.RoutingService} */
  this.grrRoutingService_ = grrRoutingService;

  /** @type {string} */
  this.selectedFilePath;

  /** @type {string} */
  this.viewMode = 'list';

  /** @type {string} */
  this.tab = 'stats';

  /** @type {number|undefined} */
  this.fileVersion;

  /** @type {string} */
  this.clientId;

  this.grrRoutingService_.uiOnParamsChanged(
      this.scope_, ['clientId', 'path', 'version', 'mode', 'tab'],
      this.onUrlRoutingParamsChanged_.bind(this));

  this.scope_.$watchGroup(['controller.selectedFilePath',
                           'controller.fileVersion',
                           'controller.viewMode',
                           'controller.tab'],
                          this.onFileContextRoutingParamsChange_.bind(this));
};



/**
 * Handles changes of the routing-related params in the URL. Updates
 * file context.
 *
 * @param {!Array<string>} params Changed routing params.
 * @private
 */
FileViewController.prototype.onUrlRoutingParamsChanged_ = function(params) {
  this.clientId = params[0];
  this.selectedFilePath = params[1];
  this.fileVersion = parseInt(params[2], 10) || undefined;
  this.viewMode = params[3] || 'list';
  this.tab = params[4] || 'stats';
};

/**
 * Handles changes of the routing-related params in the file context. Updates
 * UI routing state.
 *
 * @private
 */
FileViewController.prototype.onFileContextRoutingParamsChange_ = function() {
  var params = {
    path: this.selectedFilePath,
  };
  params['version'] = this.fileVersion || undefined;
  if (!this.viewMode || this.viewMode == 'list') {
    params['mode'] = undefined;
  } else {
    params['mode'] = this.viewMode;
  }

  if (!this.tab || this.tab == 'stats') {
    params['tab'] = undefined;
  } else {
    params['tab'] = this.tab;
  }

  this.grrRoutingService_.go('client.vfs', params);
};


/**
 * FileViewDirective definition.
 * @return {angular.Directive} Directive definition object.
 */
exports.FileViewDirective = function() {
  return {
    restrict: 'E',
    scope: {},
    templateUrl: '/static/angular-components/client/virtual-file-system/file-view.html',
    controller: FileViewController,
    controllerAs: 'controller'
  };
};


/**
 * Name of the directive in Angular.
 *
 * @const
 * @export
 */
exports.FileViewDirective.directive_name = 'grrFileView';
