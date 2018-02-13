'use strict';

goog.module('grrUi.semantic.pseudo.pseudo');
goog.module.declareLegacyNamespace();

const {FetchMoreLinkDirective} = goog.require('grrUi.semantic.pseudo.fetchMoreLinkDirective');
const {coreModule} = goog.require('grrUi.core.core');


/**
 * Module that contains definitions for "pseudo" semantic directives. Data
 * types rendered by pseudo directives don't exist on GRR server. They're
 * used purely in GRR Angular UI to make rendering easier and more
 * powerful.
 *
 * By convention pseudo types names start with a double underscore, i.e.:
 * __FetchMoreLink, etc.
 */
exports.pseudoModule =
    angular.module('grrUi.semantic.pseudo', [coreModule.name, 'ui.bootstrap']);

exports.pseudoModule.directive(
    FetchMoreLinkDirective.directive_name, FetchMoreLinkDirective);


exports.pseudoModule.run(function(grrSemanticValueDirectivesRegistryService) {
  var registry = grrSemanticValueDirectivesRegistryService;

  registry.registerDirective(
      FetchMoreLinkDirective.semantic_type, FetchMoreLinkDirective);
});
