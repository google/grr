'use strict';

goog.require('grrUi.core.module');
goog.require('grrUi.core.semanticRegistry.SemanticRegistryService');

goog.scope(function() {

describe('Semantic registry', function() {
  var testRegistry;

  beforeEach(module(grrUi.core.module.name));
  beforeEach(inject(function($injector) {
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
});

});  // goog.scope
