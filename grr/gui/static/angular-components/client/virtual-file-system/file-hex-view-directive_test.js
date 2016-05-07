'use strict';

goog.require('grrUi.client.virtualFileSystem.module');
goog.require('grrUi.tests.module');

describe('file hex view directive', function() {
  var $q, $compile, $rootScope, grrApiService;

  beforeEach(module('/static/angular-components/client/virtual-file-system/file-hex-view.html'));
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
    $rootScope.selectedFilePath = filePath;

    var template = '<grr-file-context' +
                   '    client-id="clientId"' +
                   '    selected-file-path="selectedFilePath">' +
                   '  <grr-file-hex-view />' +
                   '</grr-file-context>';
    var element = $compile(template)($rootScope);
    $rootScope.$apply();

    return element;
  };

  it('shows proper hex values', function() {
    spyOn(grrApiService, 'head').and.callFake(function() {
      return $q.when({ headers: function(){ return 100; } });
    });
    spyOn(grrApiService, 'get').and.callFake(function() {
      return $q.when({ data: 'some text' }); // Hex: 736f6d652074657874.
    });

    var element = render('C.0000111122223333', 'fs/os/c/test.txt');

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

  it('shows a hint when the file is not available', function() {
    spyOn(grrApiService, 'head').and.callFake(function() {
      return $q.reject('Some Error Message');
    });

    var element = render('C.0000111122223333', 'fs/os/c/test.txt');

    expect(grrApiService.head).toHaveBeenCalled();
    expect(element.find('.no-content').length).toEqual(1);
  });
});
