'use strict';

goog.module('grrUi.flow.flowDescriptorsTreeDirectiveTest');

const {browserTriggerEvent, testsModule} = goog.require('grrUi.tests');
const {flowModule} = goog.require('grrUi.flow.flow');


describe('flow descriptors tree directive', () => {
  let $compile;
  let $q;
  let $rootScope;
  let grrApiService;

  let emptySettingsDeferred;

  beforeEach(module(flowModule.name));
  beforeEach(module(testsModule.name));

  beforeEach(inject(($injector) => {
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
            value: {},
          },
        },
      },
    });
  }));

  afterEach(() => {
    // We have to clean document's body to remove tables we add there.
    $(document.body).html('');
  });

  const renderTestTemplate = () => {
    const template = '<grr-flow-descriptors-tree ' +
        'selected-descriptor="selectedDescriptor.value" />';
    const element = $compile(template)($rootScope);
    $rootScope.selectedDescriptor = {
      value: undefined,
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

  it('fetches descriptors from the server', () => {
    const deferred = $q.defer();
    spyOn(grrApiService, 'get').and.returnValue(deferred.promise);

    renderTestTemplate();

    expect(grrApiService.get).toHaveBeenCalledWith('/flows/descriptors');
  });

  it('fetches user settings from the server', () => {
    const deferred = $q.defer();
    spyOn(grrApiService, 'get').and.returnValue(deferred.promise);

    renderTestTemplate();

    expect(grrApiService.get).toHaveBeenCalledWith('/users/me');
  });

  it('creates node per category', (done) => {
    const deferred = $q.defer();
    spyOn(grrApiService, 'get').and.callFake((url) => {
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
                value: 'Category foo',
              },
              name: {
                type: 'RDFString',
                value: 'foo',
              },
              friendly_name: {
                type: 'RDFString',
                value: 'friendly foo',
              },
              behaviours: [{
                type: 'RDFString',
                value: 'BASIC',
              }],
            },
          },
          {
            type: 'ApiFlowDescriptor',
            value: {
              category: {
                type: 'RDFString',
                value: 'Category bar',
              },
              name: {
                type: 'RDFString',
                value: 'bar',
              },
              friendly_name: {
                type: 'RDFString',
                value: 'friendly bar',
              },
              behaviours: [{
                type: 'RDFString',
                value: 'BASIC',
              }],
            },
          },
        ],
      },
    });

    const element = renderTestTemplate();
    element.bind('DOMNodeInserted', (e) => {
      if (element.text().indexOf('Category foo') != -1 &&
          element.text().indexOf('Category bar') != -1) {
        done();
      }
    });
  });

  it('uses friendly name if available', (done) => {
    const deferred = $q.defer();
    spyOn(grrApiService, 'get').and.callFake((url) => {
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
                value: 'Category foo',
              },
              name: {
                type: 'RDFString',
                value: 'foo',
              },
              friendly_name: {
                type: 'RDFString',
                value: 'friendly foo',
              },
              behaviours: [{
                type: 'RDFString',
                value: 'BASIC',
              }],
            },
          },
        ],
      },
    });

    const element = renderTestTemplate();
    element.bind('DOMNodeInserted', (e) => {
      if (element.text().indexOf('friendly foo') != -1) {
        done();
      }
    });
  });

  it('hides flows without specified behavior', (done) => {
    const advancedSettingsDeferred = $q.defer();
    advancedSettingsDeferred.resolve({
      data: {
        value: {
          settings: {
            value: {
              mode: {
                value: 'ADVANCED',
              },
            },
          },
        },
      },
    });

    const deferred = $q.defer();
    deferred.resolve({
      data: {
        items: [
          {
            type: 'ApiFlowDescriptor',
            value: {
              category: {
                type: 'RDFString',
                value: 'Category foo',
              },
              name: {
                type: 'RDFString',
                value: 'foo',
              },
              friendly_name: {
                type: 'RDFString',
                value: 'friendly foo',
              },
              behaviours: [{
                type: 'RDFString',
                value: 'BASIC',
              }],
            },
          },
          {
            type: 'ApiFlowDescriptor',
            value: {
              category: {
                type: 'RDFString',
                value: 'Category bar',
              },
              name: {
                type: 'RDFString',
                value: 'bar',
              },
              friendly_name: {
                type: 'RDFString',
                value: 'friendly bar',
              },
              behaviours: [{
                type: 'RDFString',
                value: 'ADVANCED',
              }],
            },
          },
        ],
      },
    });

    spyOn(grrApiService, 'get').and.callFake((url) => {
      if (url == '/users/me') {
        return advancedSettingsDeferred.promise;
      } else {
        return deferred.promise;
      }
    });

    const element = renderTestTemplate();
    element.bind('DOMNodeInserted', (e) => {
      if (element.text().indexOf('friendly bar') != -1 &&
          element.text().indexOf('friendly foo') == -1) {
        done();
      }
    });
  });

  describe('when clicked', () => {
    let element;

    beforeEach((done) => {
      const deferred = $q.defer();
      spyOn(grrApiService, 'get').and.callFake((url) => {
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
                  value: 'Category 1',
                },
                name: {
                  type: 'RDFString',
                  value: 'foo',
                },
                friendly_name: {
                  type: 'RDFString',
                  value: 'friendly foo',
                },
                behaviours: [{
                  type: 'RDFString',
                  value: 'BASIC',
                }],
              },
            },
          ],
        },
      });

      element = renderTestTemplate();
      element.bind('DOMNodeInserted', (e) => {
        if (element.text().indexOf('friendly foo') != -1) {
          done();
        }
      });
    });

    it('updates selectedDescriptor binding', () => {
      expect($rootScope.selectedDescriptor.value).toBeUndefined();

      browserTriggerEvent(element.find('a:contains("Category 1")'), 'click');
      browserTriggerEvent(element.find('a:contains("friendly foo")'), 'click');
      $rootScope.$apply();

      expect($rootScope.selectedDescriptor.value).toEqual({
        type: 'ApiFlowDescriptor',
        value: {
          category: {
            type: 'RDFString',
            value: 'Category 1',
          },
          name: {
            type: 'RDFString',
            value: 'foo',
          },
          friendly_name: {
            type: 'RDFString',
            value: 'friendly foo',
          },
          behaviours: [{
            type: 'RDFString',
            value: 'BASIC',
          }],
        },
      });
    });
  });
});


exports = {};
