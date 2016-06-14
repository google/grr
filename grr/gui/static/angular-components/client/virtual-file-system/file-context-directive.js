'use strict';

goog.provide('grrUi.client.virtualFileSystem.fileContextDirective.FileContextController');
goog.provide('grrUi.client.virtualFileSystem.fileContextDirective.FileContextDirective');


goog.scope(function() {


/**
 * Controller for FileContextDirective.
 *
 * @constructor
 * @param {!angular.Scope} $scope
 * @ngInject
 */
grrUi.client.virtualFileSystem.fileContextDirective.FileContextController = function($scope) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @type {string} */
  this.clientId;

  /** @type {string} */
  this.selectedFilePath;

  /** @type {?number} */
  this.selectedFileVersion;

  this.scope_.$watchGroup(['clientId',
                           'selectedFilePath',
                           'selectedFileVersion'],
      this.onDirectiveArgumentsChange_.bind(this));

  this.scope_.$watchGroup(['controller.clientId',
                           'controller.selectedFilePath',
                           'controller.selectedFileVersion'],
      this.onControllerValuesChange_.bind(this));
};

var FileContextController =
    grrUi.client.virtualFileSystem.fileContextDirective.FileContextController;


/**
 * Is triggered whenever any value on the scope changes.
 *
 * @private
 */
FileContextController.prototype.onDirectiveArgumentsChange_ = function() {
  this.clientId = this.scope_['clientId'];
  this.selectedFilePath = this.scope_['selectedFilePath'];
  this.selectedFileVersion = this.scope_['selectedFileVersion'];
};


/**
 * Is triggered whenever any value in the controller changes.
 *
 * @private
 */
FileContextController.prototype.onControllerValuesChange_ = function() {
  this.scope_['clientId'] = this.clientId;
  this.scope_['selectedFilePath'] = this.selectedFilePath;
  this.scope_['selectedFileVersion'] = this.selectedFileVersion;
};


/**
 * Selects a file and updates the scope.
 *
 * @param {string} filePath The path to the selected file within the same folder as the previous seleciton.
 * @param {number=} opt_fileVersion The version of the selected file. If not specified, the newest will be selected.
 * @export
 */
FileContextController.prototype.selectFile = function(filePath, opt_fileVersion) {
  this.selectedFilePath = filePath;
  this.selectedFileVersion = opt_fileVersion || null;  // If opt_fileVersion is falsey, always coerce it to null.
};


/**
 * FileContextDirective definition.
 * @return {angular.Directive} Directive definition object.
 */
grrUi.client.virtualFileSystem.fileContextDirective.FileContextDirective = function() {
  return {
    restrict: 'E',
    scope: {
      clientId: '=',
      selectedFilePath: '=',
      selectedFileVersion: '='
    },
    transclude: true,
    template: '<ng-transclude />',
    controller: FileContextController,
    controllerAs: 'controller'
  };
};


/**
 * Name of the directive in Angular.
 *
 * @const
 * @export
 */
grrUi.client.virtualFileSystem.fileContextDirective.FileContextDirective.directive_name =
    'grrFileContext';

});  // goog.scope
