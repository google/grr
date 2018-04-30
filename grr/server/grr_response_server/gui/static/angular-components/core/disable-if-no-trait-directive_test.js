'use strict';

goog.module('grrUi.core.disableIfNoTraitDirectiveTest');

const {coreModule} = goog.require('grrUi.core.core');
const {testsModule} = goog.require('grrUi.tests');


describe('grr-disable-if-no-trait directive', () => {
  let $compile;
  let $q;
  let $rootScope;
  let grrApiService;


  beforeEach(module(coreModule.name));
  beforeEach(module(testsModule.name));

  beforeEach(inject(($injector) => {
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
    $q = $injector.get('$q');
    grrApiService = $injector.get('grrApiService');
  }));

  const renderTestTemplate = () => {
    const template = '<span grr-disable-if-no-trait="trait_foo"></span>';
    const element = $compile(template)($rootScope);
    $rootScope.$apply();

    return element;
  };

  it('applied "disabled" attribute if trait is missing', () => {
    const deferred = $q.defer();
    deferred.resolve({
      data: {
        value: {
          interface_traits: {
            value: {},
          },
        },
      },
    });
    spyOn(grrApiService, 'getCached').and.returnValue(deferred.promise);

    const element = renderTestTemplate();
    expect(element.attr('disabled')).toBe('disabled');
  });

  it('applied "disabled" attribute if trait is false', () => {
    const deferred = $q.defer();
    deferred.resolve({
      data: {
        value: {
          interface_traits: {
            value: {
              trait_foo: {
                value: false,
              },
            },
          },
        },
      },
    });
    spyOn(grrApiService, 'getCached').and.returnValue(deferred.promise);

    const element = renderTestTemplate();
    expect(element.attr('disabled')).toBe('disabled');
  });

  it('does nothing if trait is true', () => {
    const deferred = $q.defer();
    deferred.resolve({
      data: {
        value: {
          interface_traits: {
            value: {
              trait_foo: {
                value: true,
              },
            },
          },
        },
      },
    });
    spyOn(grrApiService, 'getCached').and.returnValue(deferred.promise);

    const element = renderTestTemplate();
    expect(element.attr('disabled')).toBe(undefined);
  });
});


exports = {};
