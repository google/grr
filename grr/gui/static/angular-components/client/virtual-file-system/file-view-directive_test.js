'use strict';

goog.require('grrUi.client.virtualFileSystem.fileViewDirective.getFileId');
goog.require('grrUi.client.virtualFileSystem.module');
goog.require('grrUi.tests.module');
goog.require('grrUi.tests.stubDirective');

describe('file view directive', function() {

  describe('getFileId()', function() {
    var getFileId = grrUi.client.virtualFileSystem.fileViewDirective.getFileId;

    it('returns the file id for any given path', function() {
      expect(getFileId('some/regular/path')).toEqual('_some-regular-path');
      expect(getFileId('some/$peci&l/path')).toEqual('_some-_24peci_26l-path');
      expect(getFileId('s0me/numb3r5/p4th')).toEqual('_s0me-numb3r5-p4th');
      expect(getFileId('a slightly/weird_/path')).toEqual('_a_20slightly-weird_5F-path');
      expect(getFileId('')).toEqual('_');
    });

    it('replaces characters with char code > 255 with more than a two-digit hex number', function() {
      expect(getFileId('some/sp€cial/path')).toEqual('_some-sp_20ACcial-path');
      expect(getFileId('fs/os/c/中国新闻网新闻中')).toEqual('_fs-os-c-_4E2D_56FD_65B0_95FB_7F51_65B0_95FB_4E2D');
    });
  });

  var $q, $compile, $rootScope, grrApiService, grrRoutingService;

  beforeEach(module('/static/angular-components/client/virtual-file-system/file-view.html'));
  beforeEach(module(grrUi.client.virtualFileSystem.module.name));
  beforeEach(module(grrUi.tests.module.name));

  grrUi.tests.stubDirective('grrFileTree');
  grrUi.tests.stubDirective('grrFileTable');
  grrUi.tests.stubDirective('grrFileDetails');

  beforeEach(inject(function($injector) {
    $q = $injector.get('$q');
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
    grrRoutingService = $injector.get('grrRoutingService');
  }));

  var render = function(clientId) {
    $rootScope.clientId = clientId;

    var template = '<grr-file-view client-id="clientId">' +
                   '</grr-file-view>';
    var element = $compile(template)($rootScope);
    $rootScope.$apply();

    return element;
  };

  it('changes global hash_state when the selected folder changes', function() {
    spyOn(grrRoutingService, 'go');

    var element = render('C.0000111122223333');
    var controller = element.controller('grrFileView');

    expect(controller).toBeDefined();
    controller.selectedFolderPath = "some/sample/folder";
    $rootScope.$apply();

    expect(grrRoutingService.go).toHaveBeenCalledWith('client.vfs',
                                                      {folder: '_some-sample-folder'});
  });
});
