'use strict';

goog.require('grrUi.flow.module');
goog.require('grrUi.tests.module');

describe('flows tree directive', function() {
  var $compile, $rootScope, $q, grrApiService;

  beforeEach(module(grrUi.flow.module.name));
  beforeEach(module(grrUi.tests.module.name));

  beforeEach(inject(function($injector) {
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
    $q = $injector.get('$q');
    grrApiService = $injector.get('grrApiService');
  }));

  afterEach(function() {
    // We have to clean document's body to remove tables we add there.
    $(document.body).html('');
  });

  var renderTestTemplate = function(flowUrn) {
    var template = '<grr-flows-tree ' +
        'selected-descriptor="selectedDescriptor.value" />';
    var element = $compile(template)($rootScope);
    $rootScope.selectedDescriptor = {
      value: undefined
    };
    $rootScope.$apply();

    // We have to add element to the body, because jsTree implementation
    // depends on element being part of the page's DOM tree.
    $(document.body).html('');
    $(document.body).append(element);

    return element;
  };

  it('fetches descriptors from the server', function() {
    var deferred = $q.defer();
    spyOn(grrApiService, 'get').and.returnValue(deferred.promise);

    renderTestTemplate();

    expect(grrApiService.get).toHaveBeenCalledWith('/flows/descriptors');
  });

  it('creates node per category', function(done) {
    var deferred = $q.defer();
    spyOn(grrApiService, 'get').and.returnValue(deferred.promise);

    deferred.resolve({
      data: {
        'Category foo': [],
        'Category bar': []
      }
    });

    var element = renderTestTemplate();
    element.bind('DOMNodeInserted', function(e) {
      if (element.text().indexOf('Category foo') != -1 &&
          element.text().indexOf('Category bar') != -1) {
        done();
      }
    });
  });

  it('uses friendly name if available', function() {
    var deferred = $q.defer();
    spyOn(grrApiService, 'get').and.returnValue(deferred.promise);

    deferred.resolve({
      data: {
        'Category 1': [
          {
            name: 'foo',
            friendly_name: 'friendly foo'
          }
        ],
      }
    });

    var element = renderTestTemplate();
    element.bind('DOMNodeInserted', function(e) {
      if (element.text().indexOf('friendly foo') != -1) {
        done();
      }
    });
  });

  describe('when clicked', function() {
    var element;

    beforeEach(function(done) {
      var deferred = $q.defer();
      spyOn(grrApiService, 'get').and.returnValue(deferred.promise);

      deferred.resolve({
        data: {
          'Category 1': [
            {
              name: 'foo',
              friendly_name: 'friendly foo'
            }
          ],
        }
      });

      element = renderTestTemplate();
      element.bind('DOMNodeInserted', function(e) {
        if (element.text().indexOf('friendly foo') != -1) {
          done();
        }
      });
    });

    it('updates selectedDescriptor binding', function() {
      expect($rootScope.selectedDescriptor.value).toBeUndefined();

      browserTrigger(element.find('a:contains("Category 1")'), 'click');
      browserTrigger(element.find('a:contains("friendly foo")'), 'click');
      $rootScope.$apply();

      expect($rootScope.selectedDescriptor.value).toEqual({
        name: 'foo',
        friendly_name: 'friendly foo'
      });
    });
  });
});
