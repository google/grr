'use strict';

goog.require('grrUi.flow.module');
goog.require('grrUi.tests.module');

describe('flow descriptors tree directive', function() {
  var $compile, $rootScope, $q, grrApiService;
  var emptySettingsDeferred;

  beforeEach(module(grrUi.flow.module.name));
  beforeEach(module(grrUi.tests.module.name));

  beforeEach(inject(function($injector) {
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
    $q = $injector.get('$q');
    grrApiService = $injector.get('grrApiService');

    // If user settings are empty, flows tree should use 'BASIC' mode.
    emptySettingsDeferred = $q.defer();
    emptySettingsDeferred.resolve({
      data: {
        value: {
          settings: {
            value: {}
          }
        }
      }
    });
  }));

  afterEach(function() {
    // We have to clean document's body to remove tables we add there.
    $(document.body).html('');
  });

  var renderTestTemplate = function(flowType) {
    var template = '<grr-flow-descriptors-tree ' +
        'flow-type="flowType" ' +
        'selected-descriptor="selectedDescriptor.value" />';
    var element = $compile(template)($rootScope);
    $rootScope.flowType = flowType;
    $rootScope.selectedDescriptor = {
      value: undefined
    };
    $rootScope.$apply();

    // We have to add element to the body, because jsTree implementation
    // depends on element being part of the page's DOM tree.
    $(document.body).html('');
    $(document.body).append(element);

    $(element.children('div.tree')[0]).on('loaded.jstree', function(e, data) {
      $(this).jstree('open_all');
    });

    return element;
  };

  it('fetches descriptors from the server', function() {
    var deferred = $q.defer();
    spyOn(grrApiService, 'get').and.returnValue(deferred.promise);

    renderTestTemplate();

    expect(grrApiService.get).toHaveBeenCalledWith('/flows/descriptors', {});
  });

  it('fetches descriptors filtered by type if flow type is specified',
     function() {
    var deferred = $q.defer();
    spyOn(grrApiService, 'get').and.returnValue(deferred.promise);

    renderTestTemplate('CLIENT');

    expect(grrApiService.get).toHaveBeenCalledWith('/flows/descriptors',
                                                   {flow_type: 'client'});
  });

  it('fetches user settings from the server', function() {
    var deferred = $q.defer();
    spyOn(grrApiService, 'get').and.returnValue(deferred.promise);

    renderTestTemplate();

    expect(grrApiService.get).toHaveBeenCalledWith('/users/me');
  });

  it('creates node per category', function(done) {
    var deferred = $q.defer();
    spyOn(grrApiService, 'get').and.callFake(function(url) {
      if (url == '/users/me') {
        return emptySettingsDeferred.promise;
      } else {
        return deferred.promise;
      }
    });

    deferred.resolve({
      data: {
        items: [
          {
            type: 'ApiFlowDescriptor',
            value: {
              category: {
                type: 'RDFString',
                value: 'Category foo'
              },
              name: {
                type: 'RDFString',
                value: 'foo'
              },
              friendly_name: {
                type: 'RDFString',
                value: 'friendly foo'
              },
              behaviours: [{
                type: 'RDFString',
                value: 'BASIC'
              }]
            }
          },
          {
            type: 'ApiFlowDescriptor',
            value: {
              category: {
                type: 'RDFString',
                value: 'Category bar'
              },
              name: {
                type: 'RDFString',
                value: 'bar'
              },
              friendly_name: {
                type: 'RDFString',
                value: 'friendly bar'
              },
              behaviours: [{
                type: 'RDFString',
                value: 'BASIC'
              }]
            }
          }
        ]
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

  it('uses friendly name if available', function(done) {
    var deferred = $q.defer();
    spyOn(grrApiService, 'get').and.callFake(function(url) {
      if (url == '/users/me') {
        return emptySettingsDeferred.promise;
      } else {
        return deferred.promise;
      }
    });

    deferred.resolve({
      data: {
        items: [
          {
            type: 'ApiFlowDescriptor',
            value: {
              category: {
                type: 'RDFString',
                value: 'Category foo'
              },
              name: {
                type: 'RDFString',
                value: 'foo'
              },
              friendly_name: {
                type: 'RDFString',
                value: 'friendly foo'
              },
              behaviours: [{
                type: 'RDFString',
                value: 'BASIC'
              }]
            }
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

  it('hides flows without specified behavior', function(done) {
    var advancedSettingsDeferred = $q.defer();
    advancedSettingsDeferred.resolve({
      data: {
        value: {
          settings: {
            value: {
              mode: {
                value: 'ADVANCED'
              }
            }
          }
        }
      }
    });

    var deferred = $q.defer();
    deferred.resolve({
      data: {
        items: [
          {
            type: 'ApiFlowDescriptor',
            value: {
              category: {
                type: 'RDFString',
                value: 'Category foo'
              },
              name: {
                type: 'RDFString',
                value: 'foo'
              },
              friendly_name: {
                type: 'RDFString',
                value: 'friendly foo'
              },
              behaviours: [{
                type: 'RDFString',
                value: 'BASIC'
              }]
            }
          },
          {
            type: 'ApiFlowDescriptor',
            value: {
              category: {
                type: 'RDFString',
                value: 'Category bar'
              },
              name: {
                type: 'RDFString',
                value: 'bar'
              },
              friendly_name: {
                type: 'RDFString',
                value: 'friendly bar'
              },
              behaviours: [{
                type: 'RDFString',
                value: 'ADVANCED'
              }]
            }
          }
        ],
      }
    });

    spyOn(grrApiService, 'get').and.callFake(function(url) {
      if (url == '/users/me') {
        return advancedSettingsDeferred.promise;
      } else {
        return deferred.promise;
      }
    });

    var element = renderTestTemplate();
    element.bind('DOMNodeInserted', function(e) {
      if (element.text().indexOf('friendly bar') != -1 &&
          element.text().indexOf('friendly foo') == -1) {
        done();
      }
    });
  });

  describe('when clicked', function() {
    var element;

    beforeEach(function(done) {
      var deferred = $q.defer();
      spyOn(grrApiService, 'get').and.callFake(function(url) {
        if (url == '/users/me') {
          return emptySettingsDeferred.promise;
        } else {
          return deferred.promise;
        }
      });

      deferred.resolve({
        data: {
          items: [
            {
              type: 'ApiFlowDescriptor',
              value: {
                category: {
                  type: 'RDFString',
                  value: 'Category 1'
                },
                name: {
                  type: 'RDFString',
                  value: 'foo'
                },
                friendly_name: {
                  type: 'RDFString',
                  value: 'friendly foo'
                },
                behaviours: [{
                  type: 'RDFString',
                value: 'BASIC'
                }]
              }
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
        type: 'ApiFlowDescriptor',
        value: {
          category: {
            type: 'RDFString',
            value: 'Category 1'
          },
          name: {
            type: 'RDFString',
            value: 'foo'
          },
          friendly_name: {
            type: 'RDFString',
            value: 'friendly foo'
          },
          behaviours: [{
            type: 'RDFString',
            value: 'BASIC'
          }]
        }
      });
    });
  });
});
