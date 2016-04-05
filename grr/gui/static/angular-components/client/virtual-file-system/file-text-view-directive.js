'use strict';

goog.provide('grrUi.client.virtualFileSystem.fileTextViewDirective.FileTextViewController');
goog.provide('grrUi.client.virtualFileSystem.fileTextViewDirective.FileTextViewDirective');


goog.scope(function() {


/**
 * Controller for FileTextViewDirective.
 *
 * @constructor
 * @param {!angular.Scope} $scope
 * @param {!grrUi.core.apiService.ApiService} grrApiService
 * @ngInject
 */
grrUi.client.virtualFileSystem.fileTextViewDirective.FileTextViewController = function(
    $scope, grrApiService) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @private {!grrUi.core.apiService.ApiService} */
  this.grrApiService_ = grrApiService;

  /** @type {string} */
  this.fileContent;

  /** @type {string} */
  this.encoding = 'UTF_8';

  /** @export {number} */
  this.page = 1;

  /** @export {number} */
  this.pageCount = 1;

  /** @private {number} */
  this.chunkSize_ = 10000;

  this.scope_.$watchGroup(['clientId', 'filePath', 'fileVersion'],
      this.onDirectiveArgumentsChange_.bind(this));
  this.scope_.$watch(function() {
    return this.encoding;
  }.bind(this), this.onEncodingChange_.bind(this));
  this.scope_.$watch(function() {
    return this.page;
  }.bind(this), this.onPageChange_.bind(this));
};

var FileTextViewController =
    grrUi.client.virtualFileSystem.fileTextViewDirective.FileTextViewController;


/**
 * Handles changes to the clientId and filePath.
 *
 * @private
 */
FileTextViewController.prototype.onDirectiveArgumentsChange_ = function() {
  var clientId = this.scope_['clientId'];
  var filePath = this.scope_['filePath'];

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
  var clientId = this.scope_['clientId'];
  var filePath = this.scope_['filePath'];
  var fileVersion = this.scope_['fileVersion'];
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
  }.bind(this));
};


/**
 * FileTextViewDirective definition.
 * @return {angular.Directive} Directive definition object.
 */
grrUi.client.virtualFileSystem.fileTextViewDirective.FileTextViewDirective = function() {
  return {
    restrict: 'E',
    scope: {
      clientId: '=',
      filePath: '=',
      fileVersion: '='
    },
    templateUrl: '/static/angular-components/client/virtual-file-system/file-text-view.html',
    controller: FileTextViewController,
    controllerAs: 'controller'
  };
};


/**
 * Name of the directive in Angular.
 *
 * @const
 * @export
 */
grrUi.client.virtualFileSystem.fileTextViewDirective.FileTextViewDirective.directive_name =
    'grrFileTextView';

});  // goog.scope
