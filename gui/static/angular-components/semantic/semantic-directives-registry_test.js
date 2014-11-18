'use strict';

goog.require('grrUi.semantic.SemanticDirectivesRegistry');

goog.scope(function() {

var SemanticDirectivesRegistry = grrUi.semantic.SemanticDirectivesRegistry;

describe('Semantic directives registry', function() {
  var prevDirectives;

  beforeEach(function() {
    prevDirectives = SemanticDirectivesRegistry.clear();
  });

  afterEach(function() {
    SemanticDirectivesRegistry.clear(prevDirectives);
  });

  it('finds previously registered directive',
     function() {
       SemanticDirectivesRegistry.registerDirective('SomeType', Object);
       var foundDirective = SemanticDirectivesRegistry.findDirectiveForMro(
           ['SomeType']);
       expect(foundDirective).toBe(Object);
     });

  it('returns undefined when searching for not registered directive',
     function() {
       var foundDirective = SemanticDirectivesRegistry.findDirectiveForMro(
           ['SomeType']);
       expect(foundDirective).toBeUndefined();
     });

  it('returns more specific directive when multiple directives match',
     function() {
       var directive1 = Object();
       var directive2 = Object();

       SemanticDirectivesRegistry.registerDirective('SomeChildType',
                                                    directive1);
       SemanticDirectivesRegistry.registerDirective('SomeParentType',
                                                    directive2);

       var foundDirective = SemanticDirectivesRegistry.findDirectiveForMro(
           ['SomeChildType', 'SomeParentType']);
       expect(foundDirective).toBe(directive1);
     });
});

});  // goog.scope
