'use strict';

goog.provide('grrUi.client.virtualFileSystem.fileHexViewDirective.FileHexViewController');
goog.provide('grrUi.client.virtualFileSystem.fileHexViewDirective.FileHexViewDirective');


goog.scope(function() {


/**
 * Controller for FileHexViewDirective.
 *
 * @constructor
 * @param {!angular.Scope} $scope
 * @param {!grrUi.core.apiService.ApiService} grrApiService
 * @ngInject
 */
grrUi.client.virtualFileSystem.fileHexViewDirective.FileHexViewController = function(
    $scope, grrApiService) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @private {!grrUi.core.apiService.ApiService} */
  this.grrApiService_ = grrApiService;

  /** @type {Array} */
  this.hexDataRows;

  /** @export {number} */
  this.page = 1;

  /** @export {number} */
  this.pageCount = 1;

  /** @private {number} */
  this.rows_ = 25;

  /** @private {number} */
  this.columns_ = 32;

  /** @private {number} */
  this.offset_ = 0;

  /** @private {number} */
  this.chunkSize_ = (this.rows_) * this.columns_;

  this.scope_.$watchGroup(['clientId', 'filePath', 'fileVersion'],
      this.onDirectiveArgumentsChange_.bind(this));
  this.scope_.$watch(function() {
    return this.page;
  }.bind(this), this.onPageChange_.bind(this));
};

var FileHexViewController =
    grrUi.client.virtualFileSystem.fileHexViewDirective.FileHexViewController;


/**
 * Handles changes to the clientId and filePath.
 *
 * @private
 */
FileHexViewController.prototype.onDirectiveArgumentsChange_ = function() {
  var clientId = this.scope_['clientId'];
  var filePath = this.scope_['filePath'];

  if (angular.isDefined(clientId) && angular.isDefined(filePath)) {
    this.fetchText_();
  }
};

/**
 * Handles changes to the selected page.
 * @param {number} page
 * @param {number} oldPage
 * @private
 */
FileHexViewController.prototype.onPageChange_ = function(page, oldPage) {
  if (this.page !== oldPage) {
    this.offset_ = (this.page - 1) * this.chunkSize_;
    this.fetchText_();
  }
};

/**
 * Fetches the file content.
 *
 * @private
 */
FileHexViewController.prototype.fetchText_ = function() {
  var clientId = this.scope_['clientId'];
  var filePath = this.scope_['filePath'];
  var fileVersion = this.scope_['fileVersion'];

  var url = 'clients/' + clientId + '/vfs-blob/' + filePath;
  var params = {};
  params['offset'] = this.offset_;
  params['length'] = this.chunkSize_;
  if (fileVersion) {
    params['timestamp'] = fileVersion;
  }

  this.grrApiService_.get(url, params).then(function(response) {
    this.parseFileContentToHexRepresentation_(response.data['content']);

    var total_size = response.data['total_size'];
    this.pageCount = Math.ceil(total_size / this.chunkSize_);
  }.bind(this));
};

/**
 * Parses the string response to a representation better suited for display.
 * @param {string} fileContent The file content as string.
 * @private
 */
FileHexViewController.prototype.parseFileContentToHexRepresentation_ = function(fileContent) {
  this.hexDataRows = [];

  if (!fileContent) {
    return;
  }

  for(var i = 0; i < this.rows_; i++){
    var rowOffset = this.offset_ + (i * this.columns_);
    this.hexDataRows.push({
      offset: rowOffset,
      data: fileContent.substr(i * this.columns_, this.columns_)
    });
  }
};

/**
 * FileHexViewDirective definition.
 * @return {angular.Directive} Directive definition object.
 */
grrUi.client.virtualFileSystem.fileHexViewDirective.FileHexViewDirective = function() {
  return {
    restrict: 'E',
    scope: {
      clientId: '=',
      filePath: '=',
      fileVersion: '='
    },
    templateUrl: '/static/angular-components/client/virtual-file-system/file-hex-view.html',
    controller: FileHexViewController,
    controllerAs: 'controller'
  };
};


/**
 * Name of the directive in Angular.
 *
 * @const
 * @export
 */
grrUi.client.virtualFileSystem.fileHexViewDirective.FileHexViewDirective.directive_name =
    'grrFileHexView';

});  // goog.scope
