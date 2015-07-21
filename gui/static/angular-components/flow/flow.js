'use strict';

goog.provide('grrUi.flow.module');

goog.require('grrUi.core.module');
goog.require('grrUi.flow.flowInfoDirective.FlowInfoDirective');
goog.require('grrUi.flow.flowLogDirective.FlowLogDirective');
goog.require('grrUi.flow.flowResultsDirective.FlowResultsDirective');
goog.require('grrUi.flow.flowsTreeDirective.FlowsTreeDirective');
goog.require('grrUi.flow.startFlowFormDirective.StartFlowFormDirective');
goog.require('grrUi.flow.startFlowViewDirective.StartFlowViewDirective');


/**
 * Angular module for flows-related UI.
 */
grrUi.flow.module = angular.module('grrUi.flow', [grrUi.core.module.name]);


grrUi.flow.module.directive(
    grrUi.flow.flowInfoDirective.FlowInfoDirective.directive_name,
    grrUi.flow.flowInfoDirective.FlowInfoDirective);
grrUi.flow.module.directive(
    grrUi.flow.flowLogDirective.FlowLogDirective.directive_name,
    grrUi.flow.flowLogDirective.FlowLogDirective);
grrUi.flow.module.directive(
    grrUi.flow.flowResultsDirective.FlowResultsDirective.directive_name,
    grrUi.flow.flowResultsDirective.FlowResultsDirective);
grrUi.flow.module.directive(
    grrUi.flow.flowsTreeDirective.FlowsTreeDirective.directive_name,
    grrUi.flow.flowsTreeDirective.FlowsTreeDirective);
grrUi.flow.module.directive(
    grrUi.flow.startFlowFormDirective.StartFlowFormDirective.directive_name,
    grrUi.flow.startFlowFormDirective.StartFlowFormDirective);
grrUi.flow.module.directive(
    grrUi.flow.startFlowViewDirective.StartFlowViewDirective.directive_name,
    grrUi.flow.startFlowViewDirective.StartFlowViewDirective);
