'use strict';

goog.provide('grrUi.semantic.pseudo.module');

goog.require('grrUi.core.module');
goog.require('grrUi.semantic.pseudo.downloadableUrnDirective.DownloadableUrnDirective');
goog.require('grrUi.semantic.pseudo.fetchMoreLinkDirective.FetchMoreLinkDirective');


/**
 * Module that contains definitions for "pseudo" semantic directives. Data
 * types rendered by pseudo directives don't exist on GRR server. They're
 * used purely in GRR Angular UI to make rendering easier and more
 * powerful.
 *
 * By convention pseudo types names start with a double underscore, i.e.:
 * __DownloadableUrn, __FetchMoreLink, etc.
 */
grrUi.semantic.pseudo.module = angular.module('grrUi.semantic.pseudo',
                                              [grrUi.core.module.name,
                                               'ui.bootstrap']);

grrUi.semantic.pseudo.module.directive(
    grrUi.semantic.pseudo.downloadableUrnDirective.DownloadableUrnDirective
        .directive_name,
    grrUi.semantic.pseudo.downloadableUrnDirective.DownloadableUrnDirective);
grrUi.semantic.pseudo.module.directive(
    grrUi.semantic.pseudo.fetchMoreLinkDirective.FetchMoreLinkDirective
        .directive_name,
    grrUi.semantic.pseudo.fetchMoreLinkDirective.FetchMoreLinkDirective);


grrUi.semantic.pseudo.module.run(
    function(grrSemanticValueDirectivesRegistryService) {

  var registry = grrSemanticValueDirectivesRegistryService;

  registry.registerDirective(
      grrUi.semantic.pseudo.downloadableUrnDirective.DownloadableUrnDirective
          .semantic_type,
      grrUi.semantic.pseudo.downloadableUrnDirective.DownloadableUrnDirective);
  registry.registerDirective(
      grrUi.semantic.pseudo.fetchMoreLinkDirective.FetchMoreLinkDirective
          .semantic_type,
      grrUi.semantic.pseudo.fetchMoreLinkDirective.FetchMoreLinkDirective);
});
