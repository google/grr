'use strict';

goog.module('grrUi.docs.docs');
goog.module.declareLegacyNamespace();

const {ApiDescriptionDirective} = goog.require('grrUi.docs.apiDescriptionDirective');
const {ApiDocsDirective} = goog.require('grrUi.docs.apiDocsDirective');
const {ApiHelperCurlService} = goog.require('grrUi.docs.apiHelperCurlService');
const {ApiHelperService} = goog.require('grrUi.docs.apiHelperService');
const {ApiQuerySpecDirective} = goog.require('grrUi.docs.apiQuerySpecDirective');
const {ApiRouteDirective} = goog.require('grrUi.docs.apiRouteDirective');
const {coreModule} = goog.require('grrUi.core.core');


/**
 * Angular module for docs-related UI.
 */
exports.docsModule = angular.module('grrUi.docs', [coreModule.name]);

exports.docsModule.directive(
    ApiDescriptionDirective.directive_name, ApiDescriptionDirective);
exports.docsModule.directive(ApiDocsDirective.directive_name, ApiDocsDirective);
exports.docsModule.directive(
    ApiRouteDirective.directive_name, ApiRouteDirective);
exports.docsModule.directive(
    ApiQuerySpecDirective.directive_name, ApiQuerySpecDirective);


exports.docsModule.service(ApiHelperService.service_name, ApiHelperService);
exports.docsModule.service(
    ApiHelperCurlService.service_name, ApiHelperCurlService);


exports.docsModule.run(function(grrApiHelperService, grrApiHelperCurlService) {
  grrApiHelperService.registerHelper('HTTP', null, grrApiHelperCurlService);
});
