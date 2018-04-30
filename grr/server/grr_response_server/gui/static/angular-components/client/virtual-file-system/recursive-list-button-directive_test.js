'use strict';

goog.module('grrUi.client.virtualFileSystem.recursiveListButtonDirectiveTest');

const {browserTriggerEvent, testsModule} = goog.require('grrUi.tests');
const {virtualFileSystemModule} = goog.require('grrUi.client.virtualFileSystem.virtualFileSystem');


describe('"recursive list directory" button', () => {
  let $compile;
  let $q;
  let $rootScope;
  let $timeout;
  let grrApiService;
  let grrReflectionService;


  beforeEach(module('/static/angular-components/client/virtual-file-system/recursive-list-button.html'));
  beforeEach(module('/static/angular-components/client/virtual-file-system/recursive-list-button-modal.html'));
  beforeEach(module(virtualFileSystemModule.name));
  beforeEach(module(testsModule.name));

  beforeEach(inject(($injector) => {
    $q = $injector.get('$q');
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
    $timeout = $injector.get('$timeout');
    grrReflectionService = $injector.get('grrReflectionService');
    grrApiService = $injector.get('grrApiService');
  }));

  const renderTestTemplate = (clientId, filePath) => {
    $rootScope.clientId = clientId || 'C.0000111122223333';
    $rootScope.filePath = filePath || 'fs/os/c/';

    const template = '<grr-recursive-list-button ' +
        'client-id="clientId" file-path="filePath" />';
    const element = $compile(template)($rootScope);
    $rootScope.$apply();

    return element;
  };

  it('fetches descriptors on click', () => {
    const deferred = $q.defer();
    spyOn(grrReflectionService, 'getRDFValueDescriptor').and.returnValue(
        deferred.promise);

    const element = renderTestTemplate();
    browserTriggerEvent(element.find('button'), 'click');

    expect(grrReflectionService.getRDFValueDescriptor).toHaveBeenCalledWith(
        'ApiCreateVfsRefreshOperationArgs', true);
  });

  describe('modal dialog', () => {
    beforeEach(() => {
      const deferred = $q.defer();
      spyOn(grrReflectionService, 'getRDFValueDescriptor').and.returnValue(
        deferred.promise);

      deferred.resolve({
        'ApiCreateVfsRefreshOperationArgs': {
          default: {
            type: 'ApiCreateVfsRefreshOperationArgs',
            value: {},
          },
        },
        'RDFInteger': {
          default: {
            type: 'RDFInteger',
            value: 0,
          },
        },
        'RDFString': {
          default: {
            type: 'RDFString',
            value: '',
          },
        },
        'ClientURN': {
          default: {
            type: 'ClientURN',
            value: '',
          },
        },
      });
    });

    afterEach(() => {
      // We have to clean document's body to remove modal windows that were not
      // closed.
      $(document.body).html('');
    });

    it('is shown when button clicked and descriptors fetched', () => {
      const element = renderTestTemplate();
      browserTriggerEvent(element.find('button'), 'click');

      expect($(document.body).text()).toContain(
          'Recursive Directory Refresh');
    });

    it('is closed when close button is clicked', () => {
      const element = renderTestTemplate();
      browserTriggerEvent($('button', element), 'click');

      browserTriggerEvent($('button.close'), 'click');
      $timeout.flush();

      expect($(document.body).text()).not.toContain(
          'Recursive Directory Refresh');
    });

    it('is closed when cancel button is clicked', () => {
      const element = renderTestTemplate();
      browserTriggerEvent($('button', element), 'click');

      browserTriggerEvent($('button[name=Cancel]'), 'click');
      $timeout.flush();

      expect($(document.body).text()).not.toContain(
          'Recursive Directory Refresh');
    });

    it('sends an API request when "refresh" is clicked', () => {
      const deferred = $q.defer();
      spyOn(grrApiService, 'post').and.returnValue(deferred.promise);

      const element = renderTestTemplate();
      browserTriggerEvent(element.find('button'), 'click');
      browserTriggerEvent($('button[name=Proceed]'), 'click');

      expect(grrApiService.post)
          .toHaveBeenCalledWith(
              'clients/C.0000111122223333/vfs-refresh-operations', {
                type: 'ApiCreateVfsRefreshOperationArgs',
                value: {
                  file_path: {
                    type: 'RDFString',
                    value: 'fs/os/c',
                  },
                  max_depth: {
                    type: 'RDFInteger',
                    value: 5,
                  },
                  notify_user: true,
                },
              },
              true);
    });

    it('strips "aff4:/" prefix from client id', () => {
      const deferred = $q.defer();
      spyOn(grrApiService, 'post').and.returnValue(deferred.promise);

      const element = renderTestTemplate('aff4:/C.0000111122223333');
      browserTriggerEvent(element.find('button'), 'click');
      browserTriggerEvent($('button[name=Proceed]'), 'click');

      expect(grrApiService.post).toHaveBeenCalled();
      expect(grrApiService.post.calls.mostRecent().args[0]).toBe(
          'clients/C.0000111122223333/vfs-refresh-operations');
    });

    it('disables the button when API request is sent', () => {
      const deferred = $q.defer();
      spyOn(grrApiService, 'post').and.returnValue(deferred.promise);

      const element = renderTestTemplate();
      browserTriggerEvent(element.find('button'), 'click');

      expect(element.find('button[disabled]').length).toBe(0);
      browserTriggerEvent($('button[name=Proceed]'), 'click');
      expect(element.find('button[disabled]').length).toBe(1);
    });

    it('shows success message when API request is successful', () => {
      const deferred = $q.defer();
      spyOn(grrApiService, 'post').and.returnValue(deferred.promise);
      deferred.resolve({
        data: {
          status: 'OK',
        },
      });

      // Polling will start immediately after POST request is successful.
      spyOn(grrApiService, 'get').and.returnValue($q.defer().promise);

      const element = renderTestTemplate();
      browserTriggerEvent(element.find('button'), 'click');
      browserTriggerEvent($('button[name=Proceed]'), 'click');

      expect($(document.body).text()).toContain(
          'Refresh started successfully!');
    });

    it('shows failure message when API request fails', () => {
      const deferred = $q.defer();
      spyOn(grrApiService, 'post').and.returnValue(deferred.promise);
      deferred.reject({
        data: {
          message: 'Oh no!',
        },
      });

      const element = renderTestTemplate();
      browserTriggerEvent(element.find('button'), 'click');
      browserTriggerEvent($('button[name=Proceed]'), 'click');

      expect($(document.body).text()).toContain(
          'Oh no!');
    });
  });
});


exports = {};
