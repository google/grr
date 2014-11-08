'use strict';

goog.provide('grrUi.core.module');

goog.require('grrUi.core.aff4Service.Aff4Service');
goog.require('grrUi.core.collectionTableDirective.CollectionTableDirective');
goog.require('grrUi.core.injectDirective.InjectDirective');


/**
 * Angular module for core GRR UI components.
 */
grrUi.core.module = angular.module('grrUi.core', ['ui.bootstrap']);


grrUi.core.module.directive(
    grrUi.core.collectionTableDirective.CollectionTableDirective.directive_name,
    grrUi.core.collectionTableDirective.CollectionTableDirective);
grrUi.core.module.directive(
    grrUi.core.injectDirective.InjectDirective.directive_name,
    grrUi.core.injectDirective.InjectDirective);
grrUi.core.module.service(
    grrUi.core.aff4Service.Aff4Service.service_name,
    grrUi.core.aff4Service.Aff4Service);
