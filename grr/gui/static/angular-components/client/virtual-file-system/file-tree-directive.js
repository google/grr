'use strict';

goog.module('grrUi.client.virtualFileSystem.fileTreeDirective');
goog.module.declareLegacyNamespace();

const {REFRESH_FOLDER_EVENT} = goog.require('grrUi.client.virtualFileSystem.events');
const {ensurePathIsFolder, getFolderFromPath} = goog.require('grrUi.client.virtualFileSystem.utils');
const {getFileId} = goog.require('grrUi.client.virtualFileSystem.fileViewDirective');


/**
 * Controller for FileTreeDirective.
 *
 * @constructor
 * @param {!angular.Scope} $rootScope
 * @param {!angular.Scope} $scope
 * @param {!angular.jQuery} $element
 * @param {!grrUi.core.apiService.ApiService} grrApiService
 * @param {!grrUi.routing.routingService.RoutingService} grrRoutingService
 * @ngInject
 */
const FileTreeController = function(
    $rootScope, $scope, $element, grrApiService, grrRoutingService) {
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

  /** @private {!grrUi.routing.routingService.RoutingService} */
  this.grrRoutingService_ = grrRoutingService;

  /** @type {!grrUi.client.virtualFileSystem.fileContextDirective.FileContextController} */
  this.fileContext;

  this.scope_.$on(REFRESH_FOLDER_EVENT,
      this.onRefreshFolderEvent_.bind(this));

  this.scope_.$watch('controller.fileContext.clientId',
      this.onClientIdChange_.bind(this));
  this.scope_.$watch('controller.fileContext.selectedFilePath',
      this.onSelectedFilePathChange_.bind(this));
};



/**
 * Handles changes of clientId binding.
 *
 * @private
 */
FileTreeController.prototype.onClientIdChange_ = function() {
  if (angular.isDefined(this.fileContext['clientId'])) {
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
      'multiple': false,
      'data' : function (node, cb) {
        if (node.id === '#') {
          controller.getChildFiles_('').then(cb);
        } else {
          controller.getChildFiles_(node.data.path).then(cb);
        }
      }
    }
  });

  this.treeElement_.on('changed.jstree', function (e, data) {
    // We're only interested in actual "select" events (not "ready" event,
    // which is sent when the node is loaded).
    if (data['action'] !== 'select_node') {
      return;
    }
    var selectionId = data.selected[0];
    var node = this.treeElement_.jstree('get_node', selectionId);
    var folderPath =  node.data.path;

    if (getFolderFromPath(this.fileContext['selectedFilePath']) === folderPath) {
      this.rootScope_.$broadcast(REFRESH_FOLDER_EVENT,
                                 ensurePathIsFolder(folderPath));
    } else {
      this.fileContext.selectFile(ensurePathIsFolder(folderPath));
    }

    // This is needed so that when user clicks on an already opened node,
    // it gets refreshed.
    var treeInstance = data['instance'];
    treeInstance['refresh_node'](data.node);
  }.bind(this));

  this.treeElement_.on('close_node.jstree', function(e, data) {
    data.node['data']['refreshOnOpen'] = true;
  }.bind(this));

  this.treeElement_.on('open_node.jstree', function(e, data) {
    if (data.node['data']['refreshOnOpen']) {
      data.node['data']['refreshOnOpen'] = false;

      var treeInstance = data['instance'];
      treeInstance['refresh_node'](data.node);
    }
  }.bind(this));

  this.treeElement_.on("loaded.jstree", function () {
    var selectedFilePath = this.fileContext['selectedFilePath'];
    if (selectedFilePath) {
      this.expandToFilePath_(getFileId(getFolderFromPath(selectedFilePath)),
                             true);
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
  var clientId_ = this.fileContext['clientId'];
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
 * Is triggered by REFRESH_FOLDER_EVENT.
 * @private
 */
FileTreeController.prototype.onRefreshFolderEvent_ = function(e, path) {
  if (angular.isUndefined(path)) {
    path = this.fileContext['selectedFilePath'];
  }

  var nodeId = getFileId(getFolderFromPath(path));
  var node = $('#' + nodeId);
  this.treeElement_.jstree(true)['refresh_node'](node);
};

/**
 * Is triggered whenever the selected folder path changes
 * @private
 */
FileTreeController.prototype.onSelectedFilePathChange_ = function() {
  var selectedFilePath = this.fileContext['selectedFilePath'];

  if (selectedFilePath) {
    var selectedFolderPath = getFolderFromPath(selectedFilePath);
    this.expandToFilePath_(getFileId(selectedFolderPath), true);
  }
};

/**
 * Selects a folder defined by the given path. If the path is not available, it
 * selects the closest parent folder.
 *
 * @param {string} filePathId The id of the folder to select.
 * @param {boolean=} opt_suppressEvent If true, no 'jstree.changed' event will
 *     be sent when the node is selected.
 * @private
 */
FileTreeController.prototype.expandToFilePath_ = function(
    filePathId, opt_suppressEvent) {
  if (!filePathId) {
    return;
  }
  var element = this.treeElement_;
  var parts = filePathId.split('-');

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
        element.jstree(true)['deselect_all'](true);
        element.jstree(true)['select_node'](node, opt_suppressEvent);
      }
    } else if (prev_node) {
      // Node can't be found, finish by selecting last available parent.
      element.jstree(true)['deselect_all'](true);
      element.jstree(true)['select_node'](prev_node, opt_suppressEvent);
    }
  }.bind(this);

  cb(0, null);
};


/**
 * FileTreeDirective definition.
 * @return {angular.Directive} Directive definition object.
 */
exports.FileTreeDirective = function() {
  return {
    restrict: 'E',
    scope: {},
    require: '^grrFileContext',
    templateUrl: '/static/angular-components/client/virtual-file-system/file-tree.html',
    controller: FileTreeController,
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
exports.FileTreeDirective.directive_name = 'grrFileTree';
