'use strict';

goog.provide('grrUi.semantic.pseudo.pseudoModule');

goog.require('grrUi.core.coreModule');
goog.require('grrUi.semantic.pseudo.fetchMoreLinkDirective.FetchMoreLinkDirective');


/**
 * Module that contains definitions for "pseudo" semantic directives. Data
 * types rendered by pseudo directives don't exist on GRR server. They're
 * used purely in GRR Angular UI to make rendering easier and more
 * powerful.
 *
 * By convention pseudo types names start with a double underscore, i.e.:
 * __FetchMoreLink, etc.
 */
grrUi.semantic.pseudo.pseudoModule = angular.module('grrUi.semantic.pseudo',
                                              [grrUi.core.coreModule.name,
                                               'ui.bootstrap']);

grrUi.semantic.pseudo.pseudoModule.directive(
    grrUi.semantic.pseudo.fetchMoreLinkDirective.FetchMoreLinkDirective
        .directive_name,
    grrUi.semantic.pseudo.fetchMoreLinkDirective.FetchMoreLinkDirective);


grrUi.semantic.pseudo.pseudoModule.run(
    function(grrSemanticValueDirectivesRegistryService) {

  var registry = grrSemanticValueDirectivesRegistryService;

  registry.registerDirective(
      grrUi.semantic.pseudo.fetchMoreLinkDirective.FetchMoreLinkDirective
          .semantic_type,
      grrUi.semantic.pseudo.fetchMoreLinkDirective.FetchMoreLinkDirective);
});
