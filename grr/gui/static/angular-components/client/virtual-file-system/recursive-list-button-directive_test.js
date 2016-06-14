'use strict';

goog.require('grrUi.client.virtualFileSystem.module');
goog.require('grrUi.tests.browserTrigger');
goog.require('grrUi.tests.module');

var browserTrigger = grrUi.tests.browserTrigger;

describe('"recursive list directory" button', function() {
  var $q, $compile, $rootScope, $timeout, grrReflectionService, grrApiService;

  beforeEach(module('/static/angular-components/client/virtual-file-system/recursive-list-button.html'));
  beforeEach(module('/static/angular-components/client/virtual-file-system/recursive-list-button-modal.html'));
  beforeEach(module(grrUi.client.virtualFileSystem.module.name));
  beforeEach(module(grrUi.tests.module.name));

  beforeEach(inject(function($injector) {
    $q = $injector.get('$q');
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
    $timeout = $injector.get('$timeout');
    grrReflectionService = $injector.get('grrReflectionService');
    grrApiService = $injector.get('grrApiService');
  }));

  var renderTestTemplate = function(clientId, filePath) {
    $rootScope.clientId = clientId || 'C.0000111122223333';
    $rootScope.filePath = filePath || 'fs/os/c/';

    var template = '<grr-recursive-list-button ' +
        'client-id="clientId" file-path="filePath" />';
    var element = $compile(template)($rootScope);
    $rootScope.$apply();

    return element;
  };

  it('fetches descriptors on click', function() {
    var deferred = $q.defer();
    spyOn(grrReflectionService, 'getRDFValueDescriptor').and.returnValue(
        deferred.promise);

    var element = renderTestTemplate();
    browserTrigger(element.find('button'), 'click');

    expect(grrReflectionService.getRDFValueDescriptor).toHaveBeenCalledWith(
        'ApiCreateVfsRefreshOperationArgs', true);
  });

  describe('modal dialog', function() {
    beforeEach(function() {
      var deferred = $q.defer();
      spyOn(grrReflectionService, 'getRDFValueDescriptor').and.returnValue(
        deferred.promise);

      deferred.resolve({
        'ApiCreateVfsRefreshOperationArgs': {
          default: {
            type: 'ApiCreateVfsRefreshOperationArgs',
            value: {}
          }
        },
        'RDFInteger': {
          default: {
            type: 'RDFInteger',
            value: 0
          }
        },
        'RDFString': {
          default: {
            type: 'RDFString',
            value: ''
          }
        },
        'ClientURN': {
          default: {
            type: 'ClientURN',
            value: ''
          }
        }
      });
    });

    afterEach(function() {
      // We have to clean document's body to remove modal windows that were not
      // closed.
      $(document.body).html('');
    });

    it('is shown when button clicked and descriptors fetched', function() {
      var element = renderTestTemplate();
      browserTrigger(element.find('button'), 'click');

      expect($(document.body).text()).toContain(
          'Recursive Refresh');
    });

    it('is closed when close button is clicked', function() {
      var element = renderTestTemplate();
      browserTrigger($('button', element), 'click');

      browserTrigger($('button.close'), 'click');
      $timeout.flush();

      expect($(document.body).text()).not.toContain(
          'Recursive Refresh');
    });

    it('is closed when cancel button is clicked', function() {
      var element = renderTestTemplate();
      browserTrigger($('button', element), 'click');

      browserTrigger($('button[name=Cancel]'), 'click');
      $timeout.flush();

      expect($(document.body).text()).not.toContain(
          'Recursive Refresh');
    });

    it('sends an API request when "refresh" is clicked', function() {
      var deferred = $q.defer();
      spyOn(grrApiService, 'post').and.returnValue(deferred.promise);

      var element = renderTestTemplate();
      browserTrigger(element.find('button'), 'click');
      browserTrigger($('button[name=Proceed]'), 'click');

      expect(grrApiService.post).toHaveBeenCalledWith(
          'clients/C.0000111122223333/vfs-refresh-operations',
          {
            type: 'ApiCreateVfsRefreshOperationArgs',
            value: {
              file_path: {
                type: 'RDFString',
                value: 'fs/os/c'
              },
              max_depth: {
                type: 'RDFInteger',
                value: 5
              },
              notify_user: true
            }
          },
          true);
    });

    it('strips "aff4:/" prefix from client id', function() {
      var deferred = $q.defer();
      spyOn(grrApiService, 'post').and.returnValue(deferred.promise);

      var element = renderTestTemplate('aff4:/C.0000111122223333');
      browserTrigger(element.find('button'), 'click');
      browserTrigger($('button[name=Proceed]'), 'click');

      expect(grrApiService.post).toHaveBeenCalled();
      expect(grrApiService.post.calls.mostRecent().args[0]).toBe(
          'clients/C.0000111122223333/vfs-refresh-operations');
    });

    it('disables the button when API request is sent', function() {
      var deferred = $q.defer();
      spyOn(grrApiService, 'post').and.returnValue(deferred.promise);

      var element = renderTestTemplate();
      browserTrigger(element.find('button'), 'click');

      expect(element.find('button[disabled]').length).toBe(0);
      browserTrigger($('button[name=Proceed]'), 'click');
      expect(element.find('button[disabled]').length).toBe(1);
    });

    it('shows success message when API request is successful', function() {
      var deferred = $q.defer();
      spyOn(grrApiService, 'post').and.returnValue(deferred.promise);
      deferred.resolve({
        data: {
          status: 'OK'
        }
      });

      var element = renderTestTemplate();
      browserTrigger(element.find('button'), 'click');
      browserTrigger($('button[name=Proceed]'), 'click');

      expect($(document.body).text()).toContain(
          'Refresh started successfully!');
    });

    it('shows failure message when API request fails', function() {
      var deferred = $q.defer();
      spyOn(grrApiService, 'post').and.returnValue(deferred.promise);
      deferred.reject({
        data: {
          message: 'Oh no!'
        }
      });

      var element = renderTestTemplate();
      browserTrigger(element.find('button'), 'click');
      browserTrigger($('button[name=Proceed]'), 'click');

      expect($(document.body).text()).toContain(
          'Oh no!');
    });
  });
});
