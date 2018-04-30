'use strict';

goog.module('grrUi.client.virtualFileSystem.vfsFilesArchiveButtonDirectiveTest');

const {DOWNLOAD_EVERYTHING_REENABLE_DELAY} = goog.require('grrUi.client.virtualFileSystem.vfsFilesArchiveButtonDirective');
const {ServerErrorButtonDirective} = goog.require('grrUi.core.serverErrorButtonDirective');
const {browserTriggerEvent, testsModule} = goog.require('grrUi.tests');
const {virtualFileSystemModule} = goog.require('grrUi.client.virtualFileSystem.virtualFileSystem');


describe('"download vfs archive" button', () => {
  let $compile;
  let $q;
  let $rootScope;
  let $timeout;
  let grrApiService;


  const ERROR_EVENT_NAME = ServerErrorButtonDirective.error_event_name;

  beforeEach(module('/static/angular-components/client/virtual-file-system/vfs-files-archive-button.html'));
  beforeEach(module(virtualFileSystemModule.name));
  beforeEach(module(testsModule.name));

  beforeEach(inject(($injector) => {
    $q = $injector.get('$q');
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
    $timeout = $injector.get('$timeout');
    grrApiService = $injector.get('grrApiService');
  }));

  const renderTestTemplate = (clientId, filePath) => {
    $rootScope.clientId = clientId || 'C.0000111122223333';
    $rootScope.filePath = filePath || 'fs/os/c/';

    const template = '<grr-vfs-files-archive-button ' +
        'client-id="clientId" file-path="filePath" />';
    const element = $compile(template)($rootScope);
    $rootScope.$apply();

    return element;
  };

  it('sends correct request when "download everything" option is chosen',
     () => {
       const deferred = $q.defer();
       spyOn(grrApiService, 'downloadFile').and.returnValue(deferred.promise);

       const element = renderTestTemplate();
       browserTriggerEvent(element.find('a[name=downloadEverything]'), 'click');

       expect(grrApiService.downloadFile)
           .toHaveBeenCalledWith(
               'clients/C.0000111122223333/vfs-files-archive/');
     });

  it('sends correct request when "download current folder" option is chosen',
     () => {
       const deferred = $q.defer();
       spyOn(grrApiService, 'downloadFile').and.returnValue(deferred.promise);

       const element = renderTestTemplate();
       browserTriggerEvent(element.find('a[name=downloadCurrentFolder]'), 'click');

       expect(grrApiService.downloadFile)
           .toHaveBeenCalledWith(
               'clients/C.0000111122223333/vfs-files-archive/fs/os/c');
     });

  it('disables "download everything" option after the click for 30 seconds',
     () => {
       const deferred = $q.defer();
       spyOn(grrApiService, 'downloadFile').and.returnValue(deferred.promise);

       const element = renderTestTemplate();
       browserTriggerEvent(element.find('a[name=downloadEverything]'), 'click');

       $timeout.flush(DOWNLOAD_EVERYTHING_REENABLE_DELAY - 1000);
       let items = element.find('li:has(a[name=downloadEverything]).disabled');
       expect(items.length).toBe(1);

       $timeout.flush(1001);
       items = element.find(
           'li:has(a[name=downloadEverything]):not(.disabled)');
       expect(items.length).toBe(1);
     });

  it('disables "download current folder" option after the click until folder is changed',
     () => {
       const deferred = $q.defer();
       spyOn(grrApiService, 'downloadFile').and.returnValue(deferred.promise);

       const element = renderTestTemplate();
       browserTriggerEvent(element.find('a[name=downloadCurrentFolder]'), 'click');

       let items = element.find(
           'li:has(a[name=downloadCurrentFolder]).disabled');
       expect(items.length).toBe(1);

       $rootScope.filePath = 'fs/os/c/d';
       $rootScope.$apply();

       items = element.find(
           'li:has(a[name=downloadCurrentFolder]):not(.disabled)');
       expect(items.length).toBe(1);
     });


  it('broadcasts error event on failure', (done) => {
    const deferred = $q.defer();
    spyOn(grrApiService, 'downloadFile').and.returnValue(deferred.promise);

    const element = renderTestTemplate();
    browserTriggerEvent(element.find('a[name=downloadCurrentFolder]'), 'click');

    $rootScope.$on(ERROR_EVENT_NAME, done);

    deferred.reject({data: {message: 'FAIL'}});
    $rootScope.$apply();
  });
});


exports = {};
