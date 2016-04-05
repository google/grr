'use strict';

goog.provide('grrUi.client.virtualFileSystem.fileTreeDirective.FileTreeController');
goog.provide('grrUi.client.virtualFileSystem.fileTreeDirective.FileTreeDirective');
goog.require('grrUi.client.virtualFileSystem.events');
goog.require('grrUi.client.virtualFileSystem.fileViewDirective.getFileId');
goog.require('grrUi.client.virtualFileSystem.fileViewDirective.getFilePath');

goog.scope(function() {

var REFRESH_FOLDER_EVENT =
    grrUi.client.virtualFileSystem.events.REFRESH_FOLDER_EVENT;

/** @type {function(string): string} */
var getFileId = grrUi.client.virtualFileSystem.fileViewDirective.getFileId;

/** @type {function(string): string} */
var getFilePath = grrUi.client.virtualFileSystem.fileViewDirective.getFilePath;


/**
 * Controller for FileTreeDirective.
 *
 * @constructor
 * @param {!angular.Scope} $rootScope
 * @param {!angular.Scope} $scope
 * @param {!angular.jQuery} $element
 * @param {!grrUi.core.apiService.ApiService} grrApiService
 * @ngInject
 */
grrUi.client.virtualFileSystem.fileTreeDirective.FileTreeController = function(
    $rootScope, $scope, $element, grrApiService) {
  /** @private {!angular.Scope} */
  this.rootScope_ = $rootScope;

  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @private {!angular.jQuery} */
  this.element_ = $element;

  /** @private {!Object} */
  this.treeElement_ = $element.find('#file-tree');

  /** @private {!grrUi.core.apiService.ApiService} */
  this.grrApiService_ = grrApiService;

  this.scope_.$watch('clientId',
      this.onClientIdChange_.bind(this));
  this.scope_.$watch('selectedFolderPath',
      this.onSelectedFolderPathChange_.bind(this));
  this.scope_.$on(REFRESH_FOLDER_EVENT,
      this.onSelectedFolderPathChange_.bind(this));
};

var FileTreeController =
    grrUi.client.virtualFileSystem.fileTreeDirective.FileTreeController;


/**
 * Handles changes of clientId binding.
 *
 * @private
 */
FileTreeController.prototype.onClientIdChange_ = function() {
  if (angular.isDefined(this.scope_['clientId'])) {
    this.initTree_();
  }
};

/**
 * Initializes the jsTree instance.
 *
 * @private
 */
FileTreeController.prototype.initTree_ = function() {
  var controller = this;
  this.treeElement_.jstree({
    'core' : {
      'data' : function (node, cb) {
        if (node.id === '#') {
          controller.getChildFiles_('').then(cb);
        } else {
          controller.getChildFiles_(node.data.path).then(cb);
        }
      }
    }
  });

  this.treeElement_.on("changed.jstree", function (e, data) {
    var selectionId = data.selected[0];
    var folderPath = getFilePath(selectionId);

    if (this.scope_['selectedFolderPath'] == folderPath) {
      this.rootScope_.$broadcast(REFRESH_FOLDER_EVENT, folderPath);
    } else {
      this.scope_['selectedFolderPath'] = folderPath;
      this.scope_['selectedFilePath'] = folderPath;
    }

    // This is needed so that when user clicks on an already opened node,
    // it gets refreshed.
    var treeInstance = data['instance'];
    treeInstance['refresh_node'](data.node);
  }.bind(this));

  this.treeElement_.bind("loaded.jstree", function () {
    var selectedFolderPath = this.scope_['selectedFolderPath'];
    if (selectedFolderPath) {
      this.expandToFolder_(selectedFolderPath);
    }
  }.bind(this));

  // Selecting a node automatically opens it
  this.treeElement_.on('select_node.jstree', function(event, data) {
    $(this)['jstree']('open_node', '#' + data.node.id);
    return true;
  });
};

/**
 * Retrieves the child directories for the current folder.
 * @param {string} folderPath The path of the current folder.
 * @return {angular.$q.Promise} A promise returning the child files when resolved.
 * @private
 */
FileTreeController.prototype.getChildFiles_ = function(folderPath) {
  var clientId_ = this.scope_['clientId'];
  var url = 'clients/' + clientId_ + '/vfs-index/' + folderPath;
  var params = { directories_only: 1 };

  return this.grrApiService_.get(url, params).then(
      this.parseFileResponse_.bind(this));
};

/**
 * Parses the API response and converts it to the structure jsTree requires.
 * @param {Object} response The server response.
 * @return {Array} A list of files in a jsTree-compatible structure.
 * @private
 */
FileTreeController.prototype.parseFileResponse_ = function(response) {
  var files = response.data['items'];

  var result = [];
  angular.forEach(files, function(file) {
    var filePath = file['value']['path']['value'];
    var fileId = getFileId(filePath);
    result.push({
      id: fileId,
      text: file['value']['name']['value'],
      data: {
        path: filePath
      },
      children: true  // always set to true to show the triangle
    });
  }.bind(this));

  return result;
};

/**
 * Is triggered whenever the selected folder path changes.
 * @private
 */
FileTreeController.prototype.onSelectedFolderPathChange_ = function() {
  var selectedFolderPath = this.scope_['selectedFolderPath'];
  this.expandToFolder_(selectedFolderPath);
};

/**
 * Selects a folder defined by the given path. If the path is not available, it selects the
 * closest parent folder.
 * @param {string} folderPath The path of the folder to select.
 * @private
 */
FileTreeController.prototype.expandToFolder_ = function(folderPath) {
  if (!folderPath) {
    return;
  }
  var element = this.treeElement_;
  var folderId = getFileId(folderPath);
  var parts = folderId.split('-');

  var cb = function(i, prev_node) {
    var id_to_open = parts.slice(0, i + 1).join('-');
    var node = $('#' + id_to_open);

    if (node.length) {
      if (parts[i + 1]) {
        // There are more nodes to go, proceed recursively.
        element.jstree('open_node', node, function() { cb(i + 1, node); },
            'no_hash');
      } else {
        // Target node: select it.
        element.jstree('select_node', node, 'no_hash');
      }
    } else if (prev_node) {
      // Node can't be found, finish by selecting last available parent.
      element.jstree('select_node', prev_node, 'no_hash');
    }
  };

  cb(0, null);
};


/**
 * FileTreeDirective definition.
 * @return {angular.Directive} Directive definition object.
 */
grrUi.client.virtualFileSystem.fileTreeDirective.FileTreeDirective = function() {
  return {
    restrict: 'E',
    scope: {
      clientId: '=',
      selectedFolderPath: '=',
      selectedFilePath: '='
    },
    templateUrl: '/static/angular-components/client/virtual-file-system/file-tree.html',
    controller: FileTreeController,
    controllerAs: 'controller'
  };
};


/**
 * Name of the directive in Angular.
 *
 * @const
 * @export
 */
grrUi.client.virtualFileSystem.fileTreeDirective.FileTreeDirective.directive_name =
    'grrFileTree';

});  // goog.scope
