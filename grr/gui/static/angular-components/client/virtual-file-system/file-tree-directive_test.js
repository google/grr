'use strict';

goog.require('grrUi.client.virtualFileSystem.module');
goog.require('grrUi.tests.browserTrigger');
goog.require('grrUi.tests.module');

var browserTrigger = grrUi.tests.browserTrigger;

describe('file tree view directive', function() {
  var $q, $compile, $rootScope, grrApiService;

  beforeEach(module('/static/angular-components/client/virtual-file-system/file-tree.html'));
  beforeEach(module(grrUi.client.virtualFileSystem.module.name));
  beforeEach(module(grrUi.tests.module.name));

  beforeEach(inject(function($injector) {
    $q = $injector.get('$q');
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
    grrApiService = $injector.get('grrApiService');
  }));

  var render = function(clientId, filePath) {
    $rootScope.clientId = clientId;
    $rootScope.selectedFolderPath = filePath;
    $rootScope.selectedFilePath = filePath;

    var template = '<grr-file-context' +
                   '    client-id="clientId"' +
                   '    selected-folder-path="selectedFolderPath"' +
                   '    selected-file-path="selectedFilePath"' +
                   '    selected-file-version="selectedFileVersion">' +
                   '  <grr-file-tree />' +
                   '</grr-file-context>';
    var element = $compile(template)($rootScope);
    $rootScope.$apply();

    return element;
  };

  var mockApiService = function(responses) {
    spyOn(grrApiService, 'get').and.callFake(function(path) {
      var response = { items: responses[path] }; // Wrap return value in type structure.
      return $q.when({ data: response });
    });
  };

  var getChildNodeTexts = function(jsTree, nodeId){
    var treeItems = jsTree.find(nodeId).find('[role=treeitem]');
    var texts = [];
    angular.forEach(treeItems, function(item) {
      texts.push($(item).text());
    });
    return texts;
  };

  it('shows correct nested folder structure', function(done) {
    var responses = {};
    responses['clients/C.0000111122223333/vfs-index/'] = [
      { value: { name: { value: 'fs' }, path: { value: 'fs' } } }];
    responses['clients/C.0000111122223333/vfs-index/fs'] = [
      { value: { name: { value: 'os' }, path: { value: 'fs/os' } } },
      { value: { name: { value: 'tsk' }, path: { value: 'fs/tsk' } } }];
    responses['clients/C.0000111122223333/vfs-index/fs/os'] = [
      { value: { name: { value: 'dir1' }, path: { value: 'fs/os/dir1' } } },
      { value: { name: { value: 'dir2' }, path: { value: 'fs/os/dir2' } } },
      { value: { name: { value: 'dir3' }, path: { value: 'fs/os/dir3' } } }];
    mockApiService(responses);

    var element = render('C.0000111122223333', 'fs');
    var jsTree = element.find('#file-tree');

    jsTree.one("load_node.jstree", function () {
      expect(jsTree.find('[role=treeitem]').length).toBe(1);
      expect(jsTree.find('[role=treeitem]').attr('id')).toBe('_fs');

      // Trigger loading of children of fs.
      browserTrigger(jsTree.find('#_fs a'), 'click');
      jsTree.one("open_node.jstree", function() {
        expect(getChildNodeTexts(jsTree, 'li#_fs')).toEqual(['os', 'tsk']);

        // Trigger loading of children of fs/os.
        browserTrigger(jsTree.find('#_fs-os a'), 'click');
        jsTree.one("open_node.jstree", function() {
          expect(getChildNodeTexts(jsTree, 'li#_fs-os')).toEqual(['dir1', 'dir2', 'dir3']);
          expect(jsTree.find('[role=treeitem]').length).toBe(6); // There should be six tree nodes in total.
          done();
        });
        $rootScope.$apply();
      });
      $rootScope.$apply();
    });
  });
});
