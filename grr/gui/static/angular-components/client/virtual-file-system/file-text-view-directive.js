'use strict';

goog.module('grrUi.client.virtualFileSystem.fileTextViewDirective');
goog.module.declareLegacyNamespace();



/**
 * Controller for FileTextViewDirective.
 *
 * @constructor
 * @param {!angular.Scope} $scope
 * @param {!grrUi.core.apiService.ApiService} grrApiService
 * @ngInject
 */
const FileTextViewController = function(
    $scope, grrApiService) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @private {!grrUi.core.apiService.ApiService} */
  this.grrApiService_ = grrApiService;

  /** @type {!grrUi.client.virtualFileSystem.fileContextDirective.FileContextController} */
  this.fileContext;

  /** @type {?string} */
  this.fileContent;

  /** @type {string} */
  this.encoding = 'UTF_8';

  /** @export {number} */
  this.page = 1;

  /** @export {number} */
  this.pageCount = 1;

  /** @private {number} */
  this.chunkSize_ = 10000;

  this.scope_.$watchGroup(['controller.fileContext.clientId',
                           'controller.fileContext.selectedFilePath',
                           'controller.fileContext.selectedFileVersion'],
      this.onContextChange_.bind(this));

  this.scope_.$watch('controller.encoding', this.onEncodingChange_.bind(this));
  this.scope_.$watch('controller.page', this.onPageChange_.bind(this));
};



/**
 * Handles changes to the clientId and filePath.
 *
 * @private
 */
FileTextViewController.prototype.onContextChange_ = function() {
  var clientId = this.fileContext['clientId'];
  var filePath = this.fileContext['selectedFilePath'];

  if (angular.isDefined(clientId) && angular.isDefined(filePath)) {
    this.fetchText_();
  }
};

/**
 * Handles changes to the encoding.
 * @param {number} page
 * @param {number} oldPage
 * @private
 */
FileTextViewController.prototype.onPageChange_ = function(page, oldPage) {
  if (this.page !== oldPage){
    this.fetchText_();
  }
};

/**
 * Handles page changes.
 * @param {string} encoding
 * @param {string} oldEncoding
 * @private
 */
FileTextViewController.prototype.onEncodingChange_ = function(encoding, oldEncoding) {
  if (this.encoding !== oldEncoding) {
    this.fetchText_();
  }
};

/**
 * Fetches the file content.
 *
 * @private
 */
FileTextViewController.prototype.fetchText_ = function() {
  var clientId = this.fileContext['clientId'];
  var filePath = this.fileContext['selectedFilePath'];
  var fileVersion = this.fileContext['selectedFileVersion'];
  var offset = (this.page - 1) * this.chunkSize_;

  var url = 'clients/' + clientId + '/vfs-text/' + filePath;
  var params = {};
  params['encoding'] = this.encoding;
  params['offset'] = offset;
  params['length'] = this.chunkSize_;
  if (fileVersion) {
    params['timestamp'] = fileVersion;
  }

  this.grrApiService_.get(url, params).then(function(response) {
    this.fileContent = response.data['content'];

    var total_size = response.data['total_size'];
    this.pageCount = Math.ceil(total_size / this.chunkSize_);
  }.bind(this), function() {
    this.fileContent = null;
  }.bind(this));
};


/**
 * FileTextViewDirective definition.
 * @return {angular.Directive} Directive definition object.
 */
exports.FileTextViewDirective = function() {
  return {
    restrict: 'E',
    scope: {},
    require: '^grrFileContext',
    templateUrl: '/static/angular-components/client/virtual-file-system/file-text-view.html',
    controller: FileTextViewController,
    controllerAs: 'controller',
    link: function(scope, element, attrs, fileContextController) {
      scope.controller.fileContext = fileContextController;
    }
  };
};


/**
 * Name of the directive in Angular.
 *
 * @const
 * @export
 */
exports.FileTextViewDirective.directive_name = 'grrFileTextView';
