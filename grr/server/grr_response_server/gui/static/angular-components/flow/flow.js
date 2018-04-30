'use strict';

goog.module('grrUi.flow.flow');
goog.module.declareLegacyNamespace();

const {ClientFlowsListDirective} = goog.require('grrUi.flow.clientFlowsListDirective');
const {ClientFlowsViewDirective} = goog.require('grrUi.flow.clientFlowsViewDirective');
const {CopyFlowFormDirective} = goog.require('grrUi.flow.copyFlowFormDirective');
const {FlowApiHelperDirective} = goog.require('grrUi.flow.flowApiHelperDirective');
const {FlowDescriptorsTreeDirective} = goog.require('grrUi.flow.flowDescriptorsTreeDirective');
const {FlowFormDirective} = goog.require('grrUi.flow.flowFormDirective');
const {FlowInfoDirective} = goog.require('grrUi.flow.flowInfoDirective');
const {FlowInspectorDirective} = goog.require('grrUi.flow.flowInspectorDirective');
const {FlowLogDirective} = goog.require('grrUi.flow.flowLogDirective');
const {FlowOverviewDirective} = goog.require('grrUi.flow.flowOverviewDirective');
const {FlowRequestsDirective} = goog.require('grrUi.flow.flowRequestsDirective');
const {FlowResultsDirective} = goog.require('grrUi.flow.flowResultsDirective');
const {FlowStatusIconDirective} = goog.require('grrUi.flow.flowStatusIconDirective');
const {FlowsListDirective} = goog.require('grrUi.flow.flowsListDirective');
const {StartFlowFormDirective} = goog.require('grrUi.flow.startFlowFormDirective');
const {StartFlowViewDirective} = goog.require('grrUi.flow.startFlowViewDirective');
const {coreModule} = goog.require('grrUi.core.core');


/**
 * Angular module for flows-related UI.
 */
exports.flowModule = angular.module('grrUi.flow', [coreModule.name]);


exports.flowModule.directive(
    ClientFlowsListDirective.directive_name, ClientFlowsListDirective);
exports.flowModule.directive(
    ClientFlowsViewDirective.directive_name, ClientFlowsViewDirective);
exports.flowModule.directive(
    CopyFlowFormDirective.directive_name, CopyFlowFormDirective);
exports.flowModule.directive(
    FlowApiHelperDirective.directive_name, FlowApiHelperDirective);
exports.flowModule.directive(
    FlowDescriptorsTreeDirective.directive_name, FlowDescriptorsTreeDirective);
exports.flowModule.directive(
    FlowFormDirective.directive_name, FlowFormDirective);
exports.flowModule.directive(
    FlowInfoDirective.directive_name, FlowInfoDirective);
exports.flowModule.directive(
    FlowInspectorDirective.directive_name, FlowInspectorDirective);
exports.flowModule.directive(FlowLogDirective.directive_name, FlowLogDirective);
exports.flowModule.directive(
    FlowOverviewDirective.directive_name, FlowOverviewDirective);
exports.flowModule.directive(
    FlowRequestsDirective.directive_name, FlowRequestsDirective);
exports.flowModule.directive(
    FlowResultsDirective.directive_name, FlowResultsDirective);
exports.flowModule.directive(
    FlowStatusIconDirective.directive_name, FlowStatusIconDirective);
exports.flowModule.directive(
    FlowsListDirective.directive_name, FlowsListDirective);
exports.flowModule.directive(
    StartFlowFormDirective.directive_name, StartFlowFormDirective);
exports.flowModule.directive(
    StartFlowViewDirective.directive_name, StartFlowViewDirective);
