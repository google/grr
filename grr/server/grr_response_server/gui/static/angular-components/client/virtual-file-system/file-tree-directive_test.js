'use strict';

goog.module('grrUi.client.virtualFileSystem.fileTreeDirectiveTest');

const {browserTriggerEvent, testsModule} = goog.require('grrUi.tests');
const {virtualFileSystemModule} = goog.require('grrUi.client.virtualFileSystem.virtualFileSystem');


describe('file tree view directive', () => {
  let $compile;
  let $q;
  let $rootScope;
  let grrApiService;


  beforeEach(module('/static/angular-components/client/virtual-file-system/file-tree.html'));
  beforeEach(module(virtualFileSystemModule.name));
  beforeEach(module(testsModule.name));

  beforeEach(inject(($injector) => {
    $q = $injector.get('$q');
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
    grrApiService = $injector.get('grrApiService');
  }));

  const render = (clientId, filePath) => {
    $rootScope.clientId = clientId;
    $rootScope.selectedFolderPath = filePath;
    $rootScope.selectedFilePath = filePath;

    const template = '<grr-file-context' +
        '    client-id="clientId"' +
        '    selected-folder-path="selectedFolderPath"' +
        '    selected-file-path="selectedFilePath"' +
        '    selected-file-version="selectedFileVersion">' +
        '  <grr-file-tree />' +
        '</grr-file-context>';
    const element = $compile(template)($rootScope);
    $rootScope.$apply();

    return element;
  };

  const mockApiService = (responses) => {
    spyOn(grrApiService, 'get').and.callFake((path) => {
      const response = {
        items: responses[path]
      };  // Wrap return value in type structure.
      return $q.when({ data: response });
    });
  };

  const getChildNodeTexts = (jsTree, nodeId) => {
    const treeItems = jsTree.find(nodeId).find('[role=treeitem]');
    const texts = [];
    angular.forEach(treeItems, (item) => {
      texts.push($(item).text());
    });
    return texts;
  };

  it('shows correct nested folder structure', (done) => {
    const responses = {};
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

    const element = render('C.0000111122223333', 'fs');
    const jsTree = element.find('#file-tree');

    jsTree.one('load_node.jstree', () => {
      expect(jsTree.find('[role=treeitem]').length).toBe(1);
      expect(jsTree.find('[role=treeitem]').attr('id')).toBe('_fs');

      // Trigger loading of children of fs.
      browserTriggerEvent(jsTree.find('#_fs a'), 'click');
      jsTree.one('open_node.jstree', () => {
        expect(getChildNodeTexts(jsTree, 'li#_fs')).toEqual(['os', 'tsk']);

        // Trigger loading of children of fs/os.
        browserTriggerEvent(jsTree.find('#_fs-os a'), 'click');
        jsTree.one('open_node.jstree', () => {
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


exports = {};
