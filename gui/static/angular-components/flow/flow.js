'use strict';

goog.provide('grrUi.flow.module');

goog.require('grrUi.core.module');
goog.require('grrUi.flow.flowLogDirective.FlowLogDirective');


/**
 * Angular module for flows-related UI.
 */
grrUi.flow.module = angular.module('grrUi.flow', [grrUi.core.module.name]);


grrUi.flow.module.directive(
    grrUi.flow.flowLogDirective.FlowLogDirective.directive_name,
    grrUi.flow.flowLogDirective.FlowLogDirective);
