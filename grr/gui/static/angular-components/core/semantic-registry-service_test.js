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

  describe('findDirectiveForMro', function() {
    it('finds previously registered directive', function() {
      testRegistry.registerDirective('SomeType', Object);
      var foundDirective = testRegistry.findDirectiveForMro(
          ['SomeType']);
      expect(foundDirective).toBe(Object);
    });

    it('returns undefined when searching for not registered directive', function() {
      var foundDirective = testRegistry.findDirectiveForMro(
          ['SomeType']);
      expect(foundDirective).toBeUndefined();
    });

    it('returns more specific directive when multiple directives match', function() {
      var directive1 = Object();
      var directive2 = Object();

      testRegistry.registerDirective('SomeChildType', directive1);
      testRegistry.registerDirective('SomeParentType', directive2);

      var foundDirective = testRegistry.findDirectiveForMro(
          ['SomeChildType', 'SomeParentType']);
      expect(foundDirective).toBe(directive1);
    });

    it('respects override for a type without directive', function() {
      var someDirective = Object();
      var foundDirective = testRegistry.findDirectiveForMro(
          ['SomeType'], {'SomeType': someDirective});
      expect(foundDirective).toBe(someDirective);
    });

    it('respects override for a single and only MRO type', function() {
      var someDirective = Object();
      var directiveOverride = Object();

      testRegistry.registerDirective('SomeType', someDirective);
      var foundDirective = testRegistry.findDirectiveForMro(
          ['SomeType'], {'SomeType': directiveOverride});
      expect(foundDirective).toBe(directiveOverride);
    });

    it('respects override for a non-leaf MRO type', function() {
      var someDirective = Object();
      var directiveOverride = Object();

      testRegistry.registerDirective('SomeParentType', someDirective);

      var foundDirective = testRegistry.findDirectiveForMro(
          ['SomeChildType', 'SomeParentType'], {'SomeParentType': directiveOverride});
      expect(foundDirective).toBe(directiveOverride);
    });

    it('respects override for a leaf MRO type', function() {
      var directive1 = Object();
      var directive2 = Object();

      testRegistry.registerDirective('SomeChildType', directive1);
      testRegistry.registerDirective('SomeParentType', directive2);

      var directiveOverride = Object();
      var foundDirective = testRegistry.findDirectiveForMro(
          ['SomeChildType', 'SomeParentType'],
          {'SomeChildType': directiveOverride});
      expect(foundDirective).toBe(directiveOverride);
    });
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

    it('returns overridden directive without using reflection', function(
        done) {
      var someDirective = Object();
      var directiveOverride = Object();
      testRegistry.registerDirective('SomeType', someDirective);

      var promise = testRegistry.findDirectiveForType(
          'SomeType', {'SomeType': directiveOverride});
      promise.then(function(value) {
        expect(value).toBe(directiveOverride);
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

    it('respects overrides for parent types', function() {
      var someDirective = Object();
      var directiveOverride = Object();
      testRegistry.registerDirective('SomeParentType', someDirective);


      var deferred = $q.defer();
      deferred.resolve({
        mro: ['SomeChildType', 'SomeParentType']
      });
      grrReflectionService.getRDFValueDescriptor = jasmine.createSpy(
          'getRDFValueDescriptor').and.returnValue(deferred.promise);

      var promise = testRegistry.findDirectiveForType(
          'SomeChildType', {'SomeParentType': directiveOverride});
      promise.then(function(value) {
        expect(grrReflectionService.getRDFValueDescriptor).toHaveBeenCalled();
        expect(value).toBe(directiveOverride);
        done();
      });
      $rootScope.$apply();
    });
  });
});

});  // goog.scope
