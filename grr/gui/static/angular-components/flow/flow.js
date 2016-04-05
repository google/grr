'use strict';

goog.provide('grrUi.flow.module');

goog.require('grrUi.core.module');
goog.require('grrUi.flow.clientFlowsListDirective.ClientFlowsListDirective');
goog.require('grrUi.flow.clientFlowsViewDirective.ClientFlowsViewDirective');
goog.require('grrUi.flow.flowDescriptorsTreeDirective.FlowDescriptorsTreeDirective');
goog.require('grrUi.flow.flowInfoDirective.FlowInfoDirective');
goog.require('grrUi.flow.flowInspectorDirective.FlowInspectorDirective');
goog.require('grrUi.flow.flowLogDirective.FlowLogDirective');
goog.require('grrUi.flow.flowResultsDirective.FlowResultsDirective');
goog.require('grrUi.flow.flowStatusIconDirective.FlowStatusIconDirective');
goog.require('grrUi.flow.flowsListDirective.FlowsListDirective');
goog.require('grrUi.flow.startFlowFormDirective.StartFlowFormDirective');
goog.require('grrUi.flow.startFlowViewDirective.StartFlowViewDirective');


/**
 * Angular module for flows-related UI.
 */
grrUi.flow.module = angular.module('grrUi.flow', [grrUi.core.module.name]);


grrUi.flow.module.directive(
    grrUi.flow.clientFlowsListDirective.ClientFlowsListDirective.directive_name,
    grrUi.flow.clientFlowsListDirective.ClientFlowsListDirective);
grrUi.flow.module.directive(
    grrUi.flow.clientFlowsViewDirective.ClientFlowsViewDirective.directive_name,
    grrUi.flow.clientFlowsViewDirective.ClientFlowsViewDirective);
grrUi.flow.module.directive(
    grrUi.flow.flowDescriptorsTreeDirective.FlowDescriptorsTreeDirective
        .directive_name,
    grrUi.flow.flowDescriptorsTreeDirective.FlowDescriptorsTreeDirective);
grrUi.flow.module.directive(
    grrUi.flow.flowInfoDirective.FlowInfoDirective.directive_name,
    grrUi.flow.flowInfoDirective.FlowInfoDirective);
grrUi.flow.module.directive(
    grrUi.flow.flowInspectorDirective.FlowInspectorDirective.directive_name,
    grrUi.flow.flowInspectorDirective.FlowInspectorDirective);
grrUi.flow.module.directive(
    grrUi.flow.flowLogDirective.FlowLogDirective.directive_name,
    grrUi.flow.flowLogDirective.FlowLogDirective);
grrUi.flow.module.directive(
    grrUi.flow.flowResultsDirective.FlowResultsDirective.directive_name,
    grrUi.flow.flowResultsDirective.FlowResultsDirective);
grrUi.flow.module.directive(
    grrUi.flow.flowStatusIconDirective.FlowStatusIconDirective.directive_name,
    grrUi.flow.flowStatusIconDirective.FlowStatusIconDirective);
grrUi.flow.module.directive(
    grrUi.flow.flowsListDirective.FlowsListDirective.directive_name,
    grrUi.flow.flowsListDirective.FlowsListDirective);
grrUi.flow.module.directive(
    grrUi.flow.startFlowFormDirective.StartFlowFormDirective.directive_name,
    grrUi.flow.startFlowFormDirective.StartFlowFormDirective);
grrUi.flow.module.directive(
    grrUi.flow.startFlowViewDirective.StartFlowViewDirective.directive_name,
    grrUi.flow.startFlowViewDirective.StartFlowViewDirective);
