'use strict';

goog.provide('grrUi.docs');
goog.provide('grrUi.docs.docsModule');

goog.require('grrUi.core');                          // USE: coreModule
goog.require('grrUi.docs.apiDescriptionDirective');  // USE: ApiDescriptionDirective
goog.require('grrUi.docs.apiDocsDirective');         // USE: ApiDocsDirective
goog.require('grrUi.docs.apiHelperCurlService');   // USE: ApiHelperCurlService
goog.require('grrUi.docs.apiHelperService');       // USE: ApiHelperService
goog.require('grrUi.docs.apiQuerySpecDirective');  // USE: ApiQuerySpecDirective
goog.require('grrUi.docs.apiRouteDirective');      // USE: ApiRouteDirective


/**
 * Angular module for docs-related UI.
 */
grrUi.docs.docsModule = angular.module('grrUi.docs', [grrUi.core.coreModule.name]);

grrUi.docs.docsModule.directive(
    grrUi.docs.apiDescriptionDirective.ApiDescriptionDirective.directive_name,
    grrUi.docs.apiDescriptionDirective.ApiDescriptionDirective);
grrUi.docs.docsModule.directive(
    grrUi.docs.apiDocsDirective.ApiDocsDirective.directive_name,
    grrUi.docs.apiDocsDirective.ApiDocsDirective);
grrUi.docs.docsModule.directive(
    grrUi.docs.apiRouteDirective.ApiRouteDirective.directive_name,
    grrUi.docs.apiRouteDirective.ApiRouteDirective);
grrUi.docs.docsModule.directive(
    grrUi.docs.apiQuerySpecDirective.ApiQuerySpecDirective.directive_name,
    grrUi.docs.apiQuerySpecDirective.ApiQuerySpecDirective);


grrUi.docs.docsModule.service(
    grrUi.docs.apiHelperService.ApiHelperService.service_name,
    grrUi.docs.apiHelperService.ApiHelperService);
grrUi.docs.docsModule.service(
    grrUi.docs.apiHelperCurlService.ApiHelperCurlService.service_name,
    grrUi.docs.apiHelperCurlService.ApiHelperCurlService);


grrUi.docs.docsModule.run(function(grrApiHelperService, grrApiHelperCurlService) {
  grrApiHelperService.registerHelper('HTTP', null, grrApiHelperCurlService);
});
