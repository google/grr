'use strict';

goog.require('grrUi.client.virtualFileSystem.module');
goog.require('grrUi.client.virtualFileSystem.vfsFilesArchiveButtonDirective.DOWNLOAD_EVERYTHING_REENABLE_DELAY');
goog.require('grrUi.core.serverErrorButtonDirective.ServerErrorButtonDirective');
goog.require('grrUi.tests.browserTrigger');
goog.require('grrUi.tests.module');

var browserTrigger = grrUi.tests.browserTrigger;

describe('"download vfs archive" button', function() {
  var $q, $compile, $rootScope, $timeout, grrApiService;

  var DOWNLOAD_EVERYTHING_REENABLE_DELAY = grrUi.client.virtualFileSystem.
      vfsFilesArchiveButtonDirective.DOWNLOAD_EVERYTHING_REENABLE_DELAY;
  var ERROR_EVENT_NAME =
      grrUi.core.serverErrorButtonDirective.ServerErrorButtonDirective
      .error_event_name;

  beforeEach(module('/static/angular-components/client/virtual-file-system/vfs-files-archive-button.html'));
  beforeEach(module(grrUi.client.virtualFileSystem.module.name));
  beforeEach(module(grrUi.tests.module.name));

  beforeEach(inject(function($injector) {
    $q = $injector.get('$q');
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
    $timeout = $injector.get('$timeout');
    grrApiService = $injector.get('grrApiService');
  }));

  var renderTestTemplate = function(clientId, filePath) {
    $rootScope.clientId = clientId || 'C.0000111122223333';
    $rootScope.filePath = filePath || 'fs/os/c/';

    var template = '<grr-vfs-files-archive-button ' +
        'client-id="clientId" file-path="filePath" />';
    var element = $compile(template)($rootScope);
    $rootScope.$apply();

    return element;
  };

  it('sends correct request when "download everything" option is chosen', function() {
    var deferred = $q.defer();
    spyOn(grrApiService, 'downloadFile').and.returnValue(deferred.promise);

    var element = renderTestTemplate();
    browserTrigger(element.find('a[name=downloadEverything]'), 'click');

    expect(grrApiService.downloadFile).toHaveBeenCalledWith(
        'clients/C.0000111122223333/vfs-files-archive/');
  });

  it('sends correct request when "download current folder" option is chosen', function() {
    var deferred = $q.defer();
    spyOn(grrApiService, 'downloadFile').and.returnValue(deferred.promise);

    var element = renderTestTemplate();
    browserTrigger(element.find('a[name=downloadCurrentFolder]'), 'click');

    expect(grrApiService.downloadFile).toHaveBeenCalledWith(
        'clients/C.0000111122223333/vfs-files-archive/fs/os/c');
  });

  it('disables "download everything" option after the click for 30 seconds', function() {
    var deferred = $q.defer();
    spyOn(grrApiService, 'downloadFile').and.returnValue(deferred.promise);

    var element = renderTestTemplate();
    browserTrigger(element.find('a[name=downloadEverything]'), 'click');

    $timeout.flush(DOWNLOAD_EVERYTHING_REENABLE_DELAY - 1000);
    expect(element.find('li:has(a[name=downloadEverything]).disabled').length)
        .toBe(1);

    $timeout.flush(1001);
    expect(element.find('li:has(a[name=downloadEverything]):not(.disabled)').length)
        .toBe(1);
  });

  it('disables "download current folder" option after the click until folder is changed', function() {
    var deferred = $q.defer();
    spyOn(grrApiService, 'downloadFile').and.returnValue(deferred.promise);

    var element = renderTestTemplate();
    browserTrigger(element.find('a[name=downloadCurrentFolder]'), 'click');

    expect(element.find('li:has(a[name=downloadCurrentFolder]).disabled').length)
        .toBe(1);

    $rootScope.filePath = 'fs/os/c/d';
    $rootScope.$apply();

    expect(element.find('li:has(a[name=downloadCurrentFolder]):not(.disabled)').length)
        .toBe(1);
  });


  it('broadcasts error event on failure', function(done) {
    var deferred = $q.defer();
    spyOn(grrApiService, 'downloadFile').and.returnValue(deferred.promise);

    var element = renderTestTemplate();
    browserTrigger(element.find('a[name=downloadCurrentFolder]'), 'click');

    $rootScope.$on(ERROR_EVENT_NAME, done);

    deferred.reject({data: {message: 'FAIL'}});
    $rootScope.$apply();
  });
});
