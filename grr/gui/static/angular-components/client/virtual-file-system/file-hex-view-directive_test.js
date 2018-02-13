'use strict';

goog.module('grrUi.client.virtualFileSystem.fileHexViewDirectiveTest');

const {testsModule} = goog.require('grrUi.tests');
const {virtualFileSystemModule} = goog.require('grrUi.client.virtualFileSystem.virtualFileSystem');


describe('file hex view directive', () => {
  let $compile;
  let $q;
  let $rootScope;
  let grrApiService;


  beforeEach(module('/static/angular-components/client/virtual-file-system/file-hex-view.html'));
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
    $rootScope.selectedFilePath = filePath;

    const template = '<grr-file-context' +
        '    client-id="clientId"' +
        '    selected-file-path="selectedFilePath">' +
        '  <grr-file-hex-view />' +
        '</grr-file-context>';
    const element = $compile(template)($rootScope);
    $rootScope.$apply();

    return element;
  };

  it('shows proper hex values', () => {
    spyOn(grrApiService, 'head').and.callFake(() => $q.when({
      headers: function() {
        return 100;
      }
    }));
    spyOn(grrApiService, 'get').and.callFake(() => $q.when({
      data: 'some text'
    }));

    const element = render('C.0000111122223333', 'fs/os/c/test.txt');

    expect(grrApiService.get).toHaveBeenCalled();
    expect(element.find('table.offset-area tr:first-child td').text().trim())
        .toEqual('0x00000000');
    expect(element.find('table.offset-area tr:last-child td').text().trim())
        .toEqual('0x00000300');
    expect(element.find('table.hex-area tr:first-child td').text().trim())
        .toEqual('736f6d652074657874');
    expect(element.find('table.content-area tr:first-child td').text().trim())
        .toEqual('some text');
  });

  it('shows a hint when the file is not available', () => {
    spyOn(grrApiService, 'head')
        .and.callFake(() => $q.reject('Some Error Message'));

    const element = render('C.0000111122223333', 'fs/os/c/test.txt');

    expect(grrApiService.head).toHaveBeenCalled();
    expect(element.find('.no-content').length).toEqual(1);
  });
});


exports = {};
