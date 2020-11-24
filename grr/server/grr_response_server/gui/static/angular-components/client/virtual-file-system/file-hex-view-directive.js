goog.module('grrUi.client.virtualFileSystem.fileHexViewDirective');
goog.module.declareLegacyNamespace();

const apiService = goog.requireType('grrUi.core.apiService');
const fileContextDirective = goog.requireType('grrUi.client.virtualFileSystem.fileContextDirective');



/**
 * Controller for FileHexViewDirective.
 * @unrestricted
 */
const FileHexViewController = class {
  /**
   * @param {!angular.Scope} $scope
   * @param {!apiService.ApiService} grrApiService
   * @ngInject
   */
  constructor($scope, grrApiService) {
    /** @private {!angular.Scope} */
    this.scope_ = $scope;

    /** @private {!apiService.ApiService} */
    this.grrApiService_ = grrApiService;

    /**
     * @type {!fileContextDirective.FileContextController}
     */
    this.fileContext;

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

    this.scope_.$watchGroup(
        [
          'controller.fileContext.clientId',
          'controller.fileContext.selectedFilePath',
          'controller.fileContext.selectedFileVersion'
        ],
        this.onContextChange_.bind(this));

    this.scope_.$watch('controller.page', this.onPageChange_.bind(this));
  }

  /**
   * Handles changes to the clientId and filePath.
   *
   * @private
   */
  onContextChange_() {
    var clientId = this.fileContext['clientId'];
    var filePath = this.fileContext['selectedFilePath'];

    if (angular.isDefined(clientId) && angular.isDefined(filePath)) {
      this.fetchText_();
    }
  }

  /**
   * Handles changes to the selected page.
   * @param {number} page
   * @param {number} oldPage
   * @private
   */
  onPageChange_(page, oldPage) {
    if (this.page !== oldPage) {
      this.offset_ = (this.page - 1) * this.chunkSize_;
      this.fetchText_();
    }
  }

  /**
   * Fetches the file content.
   *
   * @private
   */
  fetchText_() {
    var clientId = this.fileContext['clientId'];
    var filePath = this.fileContext['selectedFilePath'];
    var fileVersion = this.fileContext['selectedFileVersion'];

    var url = 'clients/' + clientId + '/vfs-blob/' + filePath;
    var headParams = {};
    if (fileVersion) {
      headParams['timestamp'] = fileVersion;
    }

    // We first need to get the content length via HEAD, passing no offset and
    // no length.
    this.grrApiService_.head(url, headParams)
        .then(function(response) {
          var total_size = response.headers('Content-Length');
          this.pageCount = Math.ceil(total_size / this.chunkSize_);

          var params = {};
          params['offset'] = this.offset_;
          params['length'] = this.chunkSize_;
          if (fileVersion) {
            params['timestamp'] = fileVersion;
          }
          return this.grrApiService_.get(url, params);
        }.bind(this))
        .then(
            function(response) {
              this.parseFileContentToHexRepresentation_(response.data);
            }.bind(this),
            function() {
              this.hexDataRows = null;
            }.bind(this));
  }

  /**
   * Parses the string response to a representation better suited for display.
   *
   * @param {string} fileContent The file content as string.
   * @private
   */
  parseFileContentToHexRepresentation_(fileContent) {
    this.hexDataRows = [];

    if (!fileContent) {
      return;
    }

    for (var i = 0; i < this.rows_; i++) {
      var rowOffset = this.offset_ + (i * this.columns_);
      this.hexDataRows.push({
        offset: rowOffset,
        data: fileContent.substr(i * this.columns_, this.columns_)
      });
    }
  }
};



/**
 * FileHexViewDirective definition.
 *
 * @return {angular.Directive} Directive definition object.
 */
exports.FileHexViewDirective = function() {
  return {
    restrict: 'E',
    scope: {},
    require: '^grrFileContext',
    templateUrl:
        '/static/angular-components/client/virtual-file-system/file-hex-view.html',
    controller: FileHexViewController,
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
exports.FileHexViewDirective.directive_name = 'grrFileHexView';
