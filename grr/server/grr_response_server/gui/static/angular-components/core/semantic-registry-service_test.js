'use strict';

goog.module('grrUi.core.semanticRegistryServiceTest');

const {SemanticRegistryService} = goog.require('grrUi.core.semanticRegistryService');
const {coreModule} = goog.require('grrUi.core.core');


describe('Semantic registry', () => {
  let $q;
  let $rootScope;
  let grrReflectionService;
  let testRegistry;


  beforeEach(module(coreModule.name));
  beforeEach(inject(($injector) => {
    $rootScope = $injector.get('$rootScope');
    $q = $injector.get('$q');
    grrReflectionService = $injector.get('grrReflectionService');

    testRegistry = $injector.instantiate(SemanticRegistryService, {});
  }));

  describe('findDirectiveForMro', () => {
    it('finds previously registered directive', () => {
      testRegistry.registerDirective('SomeType', Object);
      const foundDirective = testRegistry.findDirectiveForMro(['SomeType']);
      expect(foundDirective).toBe(Object);
    });

    it('returns undefined when searching for not registered directive', () => {
      const foundDirective = testRegistry.findDirectiveForMro(['SomeType']);
      expect(foundDirective).toBeUndefined();
    });

    it('returns more specific directive when multiple directives match', () => {
      const directive1 = Object();
      const directive2 = Object();

      testRegistry.registerDirective('SomeChildType', directive1);
      testRegistry.registerDirective('SomeParentType', directive2);

      const foundDirective =
          testRegistry.findDirectiveForMro(['SomeChildType', 'SomeParentType']);
      expect(foundDirective).toBe(directive1);
    });

    it('respects override for a type without directive', () => {
      const someDirective = Object();
      const foundDirective = testRegistry.findDirectiveForMro(
          ['SomeType'], {'SomeType': someDirective});
      expect(foundDirective).toBe(someDirective);
    });

    it('respects override for a single and only MRO type', () => {
      const someDirective = Object();
      const directiveOverride = Object();

      testRegistry.registerDirective('SomeType', someDirective);
      const foundDirective = testRegistry.findDirectiveForMro(
          ['SomeType'], {'SomeType': directiveOverride});
      expect(foundDirective).toBe(directiveOverride);
    });

    it('respects override for a non-leaf MRO type', () => {
      const someDirective = Object();
      const directiveOverride = Object();

      testRegistry.registerDirective('SomeParentType', someDirective);

      const foundDirective = testRegistry.findDirectiveForMro(
          ['SomeChildType', 'SomeParentType'],
          {'SomeParentType': directiveOverride});
      expect(foundDirective).toBe(directiveOverride);
    });

    it('respects override for a leaf MRO type', () => {
      const directive1 = Object();
      const directive2 = Object();

      testRegistry.registerDirective('SomeChildType', directive1);
      testRegistry.registerDirective('SomeParentType', directive2);

      const directiveOverride = Object();
      const foundDirective = testRegistry.findDirectiveForMro(
          ['SomeChildType', 'SomeParentType'],
          {'SomeChildType': directiveOverride});
      expect(foundDirective).toBe(directiveOverride);
    });
  });

  describe('findDirectiveByType', () => {
    it('returns registered directive without using reflection', (done) => {
      testRegistry.registerDirective('SomeType', Object);
      const promise = testRegistry.findDirectiveForType('SomeType');
      promise.then((value) => {
        expect(value).toBe(Object);
        done();
      });
      $rootScope.$apply();
    });

    it('returns overridden directive without using reflection', (done) => {
      const someDirective = Object();
      const directiveOverride = Object();
      testRegistry.registerDirective('SomeType', someDirective);

      const promise = testRegistry.findDirectiveForType(
          'SomeType', {'SomeType': directiveOverride});
      promise.then((value) => {
        expect(value).toBe(directiveOverride);
        done();
      });
      $rootScope.$apply();
    });

    it('queries reflection service for MRO if type unregistered', (done) => {
      testRegistry.registerDirective('SomeParentType', Object);

      const deferred = $q.defer();
      deferred.resolve({
        mro: ['SomeChildType', 'SomeParentType'],
      });
      grrReflectionService.getRDFValueDescriptor =
          jasmine.createSpy('getRDFValueDescriptor')
              .and.returnValue(deferred.promise);

      const promise = testRegistry.findDirectiveForType('SomeChildType');
      promise.then((value) => {
        expect(grrReflectionService.getRDFValueDescriptor).toHaveBeenCalled();
        expect(value).toBe(Object);
        done();
      });
      $rootScope.$apply();
    });

    it('respects overrides for parent types', () => {
      const someDirective = Object();
      const directiveOverride = Object();
      testRegistry.registerDirective('SomeParentType', someDirective);


      const deferred = $q.defer();
      deferred.resolve({
        mro: ['SomeChildType', 'SomeParentType'],
      });
      grrReflectionService.getRDFValueDescriptor =
          jasmine.createSpy('getRDFValueDescriptor')
              .and.returnValue(deferred.promise);

      const promise = testRegistry.findDirectiveForType(
          'SomeChildType', {'SomeParentType': directiveOverride});
      promise.then((value) => {
        expect(grrReflectionService.getRDFValueDescriptor).toHaveBeenCalled();
        expect(value).toBe(directiveOverride);
        done();
      });
      $rootScope.$apply();
    });
  });
});


exports = {};
