'use strict';

goog.require('grrUi.core.module');
goog.require('grrUi.tests.module');


describe('grr-disable-if-no-trait directive', function() {
  var $compile, $rootScope, $q, grrApiService;

  beforeEach(module(grrUi.core.module.name));
  beforeEach(module(grrUi.tests.module.name));

  beforeEach(inject(function($injector) {
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
    $q = $injector.get('$q');
    grrApiService = $injector.get('grrApiService');
  }));

  var renderTestTemplate = function() {
    var template = '<span grr-disable-if-no-trait="trait_foo"></span>';
    var element = $compile(template)($rootScope);
    $rootScope.$apply();

    return element;
  };

  it('applied "disabled" attribute if trait is missing', function() {
    var deferred = $q.defer();
    deferred.resolve({
      data: {
        value: {
          interface_traits: {
            value: {}
          }
        }
      }
    });
    spyOn(grrApiService, 'getCached').and.returnValue(deferred.promise);

    var element = renderTestTemplate();
    expect(element.attr('disabled')).toBe('disabled');
  });

  it('applied "disabled" attribute if trait is false', function() {
    var deferred = $q.defer();
    deferred.resolve({
      data: {
        value: {
          interface_traits: {
            value: {
              trait_foo: {
                value: false
              }
            }
          }
        }
      }
    });
    spyOn(grrApiService, 'getCached').and.returnValue(deferred.promise);

    var element = renderTestTemplate();
    expect(element.attr('disabled')).toBe('disabled');
  });

  it('does nothing if trait is true', function() {
    var deferred = $q.defer();
    deferred.resolve({
      data: {
        value: {
          interface_traits: {
            value: {
              trait_foo: {
                value: true
              }
            }
          }
        }
      }
    });
    spyOn(grrApiService, 'getCached').and.returnValue(deferred.promise);

    var element = renderTestTemplate();
    expect(element.attr('disabled')).toBe(undefined);
  });

});
