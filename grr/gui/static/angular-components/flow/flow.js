'use strict';

goog.provide('grrUi.flow');
goog.provide('grrUi.flow.flowModule');

goog.require('grrUi.core');                           // USE: coreModule
goog.require('grrUi.flow.clientFlowsListDirective');  // USE: ClientFlowsListDirective
goog.require('grrUi.flow.clientFlowsViewDirective');  // USE: ClientFlowsViewDirective
goog.require('grrUi.flow.copyFlowFormDirective');  // USE: CopyFlowFormDirective
goog.require('grrUi.flow.flowApiHelperDirective');  // USE: FlowApiHelperDirective
goog.require('grrUi.flow.flowDescriptorsTreeDirective');  // USE: FlowDescriptorsTreeDirective
goog.require('grrUi.flow.flowFormDirective');       // USE: FlowFormDirective
goog.require('grrUi.flow.flowInfoDirective');       // USE: FlowInfoDirective
goog.require('grrUi.flow.flowInspectorDirective');  // USE: FlowInspectorDirective
goog.require('grrUi.flow.flowLogDirective');        // USE: FlowLogDirective
goog.require('grrUi.flow.flowOverviewDirective');  // USE: FlowOverviewDirective
goog.require('grrUi.flow.flowRequestsDirective');  // USE: FlowRequestsDirective
goog.require('grrUi.flow.flowResultsDirective');   // USE: FlowResultsDirective
goog.require('grrUi.flow.flowStatusIconDirective');  // USE: FlowStatusIconDirective
goog.require('grrUi.flow.flowsListDirective');       // USE: FlowsListDirective
goog.require('grrUi.flow.startFlowFormDirective');  // USE: StartFlowFormDirective
goog.require('grrUi.flow.startFlowViewDirective');  // USE: StartFlowViewDirective


/**
 * Angular module for flows-related UI.
 */
grrUi.flow.flowModule = angular.module('grrUi.flow', [grrUi.core.coreModule.name]);


grrUi.flow.flowModule.directive(
    grrUi.flow.clientFlowsListDirective.ClientFlowsListDirective.directive_name,
    grrUi.flow.clientFlowsListDirective.ClientFlowsListDirective);
grrUi.flow.flowModule.directive(
    grrUi.flow.clientFlowsViewDirective.ClientFlowsViewDirective.directive_name,
    grrUi.flow.clientFlowsViewDirective.ClientFlowsViewDirective);
grrUi.flow.flowModule.directive(
    grrUi.flow.copyFlowFormDirective.CopyFlowFormDirective.directive_name,
    grrUi.flow.copyFlowFormDirective.CopyFlowFormDirective);
grrUi.flow.flowModule.directive(
    grrUi.flow.flowApiHelperDirective.FlowApiHelperDirective.directive_name,
    grrUi.flow.flowApiHelperDirective.FlowApiHelperDirective);
grrUi.flow.flowModule.directive(
    grrUi.flow.flowDescriptorsTreeDirective.FlowDescriptorsTreeDirective
        .directive_name,
    grrUi.flow.flowDescriptorsTreeDirective.FlowDescriptorsTreeDirective);
grrUi.flow.flowModule.directive(
    grrUi.flow.flowFormDirective.FlowFormDirective.directive_name,
    grrUi.flow.flowFormDirective.FlowFormDirective);
grrUi.flow.flowModule.directive(
    grrUi.flow.flowInfoDirective.FlowInfoDirective.directive_name,
    grrUi.flow.flowInfoDirective.FlowInfoDirective);
grrUi.flow.flowModule.directive(
    grrUi.flow.flowInspectorDirective.FlowInspectorDirective.directive_name,
    grrUi.flow.flowInspectorDirective.FlowInspectorDirective);
grrUi.flow.flowModule.directive(
    grrUi.flow.flowLogDirective.FlowLogDirective.directive_name,
    grrUi.flow.flowLogDirective.FlowLogDirective);
grrUi.flow.flowModule.directive(
    grrUi.flow.flowOverviewDirective.FlowOverviewDirective.directive_name,
    grrUi.flow.flowOverviewDirective.FlowOverviewDirective);
grrUi.flow.flowModule.directive(
    grrUi.flow.flowRequestsDirective.FlowRequestsDirective.directive_name,
    grrUi.flow.flowRequestsDirective.FlowRequestsDirective);
grrUi.flow.flowModule.directive(
    grrUi.flow.flowResultsDirective.FlowResultsDirective.directive_name,
    grrUi.flow.flowResultsDirective.FlowResultsDirective);
grrUi.flow.flowModule.directive(
    grrUi.flow.flowStatusIconDirective.FlowStatusIconDirective.directive_name,
    grrUi.flow.flowStatusIconDirective.FlowStatusIconDirective);
grrUi.flow.flowModule.directive(
    grrUi.flow.flowsListDirective.FlowsListDirective.directive_name,
    grrUi.flow.flowsListDirective.FlowsListDirective);
grrUi.flow.flowModule.directive(
    grrUi.flow.startFlowFormDirective.StartFlowFormDirective.directive_name,
    grrUi.flow.startFlowFormDirective.StartFlowFormDirective);
grrUi.flow.flowModule.directive(
    grrUi.flow.startFlowViewDirective.StartFlowViewDirective.directive_name,
    grrUi.flow.startFlowViewDirective.StartFlowViewDirective);
