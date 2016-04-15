'use strict';

goog.require('grrUi.core.module');
goog.require('grrUi.core.semanticRegistry.SemanticRegistryService');

goog.scope(function() {

describe('Semantic registry', function() {
  var $rootScope, $q, grrReflectionService, testRegistry;

  beforeEach(module(grrUi.core.module.name));
  beforeEach(inject(function($injector) {
    $rootScope = $injector.get('$rootScope');
    $q = $injector.get('$q');
    grrReflectionService = $injector.get('grrReflectionService');

    testRegistry = $injector.instantiate(
        grrUi.core.semanticRegistry.SemanticRegistryService, {});
  }));

  it('finds previously registered directive',
     function() {
       testRegistry.registerDirective('SomeType', Object);
       var foundDirective = testRegistry.findDirectiveForMro(
           ['SomeType']);
       expect(foundDirective).toBe(Object);
     });

  it('returns undefined when searching for not registered directive',
     function() {
       var foundDirective = testRegistry.findDirectiveForMro(
           ['SomeType']);
       expect(foundDirective).toBeUndefined();
     });

  it('returns more specific directive when multiple directives match',
     function() {
       var directive1 = Object();
       var directive2 = Object();

       testRegistry.registerDirective('SomeChildType', directive1);
       testRegistry.registerDirective('SomeParentType', directive2);

       var foundDirective = testRegistry.findDirectiveForMro(
           ['SomeChildType', 'SomeParentType']);
       expect(foundDirective).toBe(directive1);
     });

  describe('findDirectiveByType', function() {
    it('returns registered directive without using reflection', function(
        done) {
      testRegistry.registerDirective('SomeType', Object);
      var promise = testRegistry.findDirectiveForType(
          'SomeType');
      promise.then(function(value) {
        expect(value).toBe(Object);
        done();
      });
      $rootScope.$apply();
    });

    it('queries reflection service for MRO if type unregistered', function(
        done) {
      testRegistry.registerDirective('SomeParentType', Object);

      var deferred = $q.defer();
      deferred.resolve({
        mro: ['SomeChildType', 'SomeParentType']
      });
      grrReflectionService.getRDFValueDescriptor = jasmine.createSpy(
          'getRDFValueDescriptor').and.returnValue(deferred.promise);

      var promise = testRegistry.findDirectiveForType(
          'SomeChildType');
      promise.then(function(value) {
        expect(grrReflectionService.getRDFValueDescriptor).toHaveBeenCalled();
        expect(value).toBe(Object);
        done();
      });
      $rootScope.$apply();
    });
  });
});

});  // goog.scope
