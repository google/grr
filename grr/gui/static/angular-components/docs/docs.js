'use strict';

goog.provide('grrUi.docs.module');

goog.require('grrUi.core.module');
goog.require('grrUi.docs.apiDescriptionDirective.ApiDescriptionDirective');
goog.require('grrUi.docs.apiDocsDirective.ApiDocsDirective');
goog.require('grrUi.docs.apiQuerySpecDirective.ApiQuerySpecDirective');
goog.require('grrUi.docs.apiRouteDirective.ApiRouteDirective');


/**
 * Angular module for docs-related UI.
 */
grrUi.docs.module = angular.module('grrUi.docs', [grrUi.core.module.name]);

grrUi.docs.module.directive(
    grrUi.docs.apiDescriptionDirective.ApiDescriptionDirective.directive_name,
    grrUi.docs.apiDescriptionDirective.ApiDescriptionDirective);
grrUi.docs.module.directive(
    grrUi.docs.apiDocsDirective.ApiDocsDirective.directive_name,
    grrUi.docs.apiDocsDirective.ApiDocsDirective);
grrUi.docs.module.directive(
    grrUi.docs.apiRouteDirective.ApiRouteDirective.directive_name,
    grrUi.docs.apiRouteDirective.ApiRouteDirective);
grrUi.docs.module.directive(
    grrUi.docs.apiQuerySpecDirective.ApiQuerySpecDirective.directive_name,
    grrUi.docs.apiQuerySpecDirective.ApiQuerySpecDirective);
