'use strict';

goog.require('grrUi.semantic.rekall.module');
goog.require('grrUi.semantic.rekall.rekallRegistry.RekallRegistryService');

goog.scope(function() {

describe('Rekall registry', function() {

  var grrRekallDirectivesRegistryService, testRegistry;

  beforeEach(module(grrUi.semantic.rekall.module.name));
  beforeEach(inject(function($injector) {
    grrRekallDirectivesRegistryService = $injector.get(
        'grrRekallDirectivesRegistryService');

    testRegistry = $injector.instantiate(
        grrUi.semantic.rekall.rekallRegistry.RekallRegistryService, {});
  }));

  it('finds previously registered directive', function() {
    testRegistry.registerDirective('SomeType', Object);
    var foundDirective = testRegistry.findDirectiveForMro('SomeType');
    expect(foundDirective).toBe(Object);
  });

  it('returns undefined when searching for not registered directive',
      function() {
    var foundDirective = testRegistry.findDirectiveForMro('SomeType');
    expect(foundDirective).toBeUndefined();
  });

  it('returns more specific directive when multiple directives match',
      function() {
    var directive1 = Object();
    var directive2 = Object();

    testRegistry.registerDirective('SomeChildType', directive1);
    testRegistry.registerDirective('SomeParentType', directive2);

    var foundDirective = testRegistry.findDirectiveForMro(
       'SomeChildType:SomeParentType');
    expect(foundDirective).toBe(directive1);
  });

});

});  // goog.scope
