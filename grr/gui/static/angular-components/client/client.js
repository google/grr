'use strict';

goog.provide('grrUi.client.module');
goog.require('grrUi.client.addClientsLabelsDialogDirective.AddClientsLabelsDialogDirective');
goog.require('grrUi.client.clientCrashesDirective.ClientCrashesDirective');
goog.require('grrUi.client.clientDialogService.ClientDialogService');
goog.require('grrUi.client.clientLoadViewDirective.ClientLoadViewDirective');
goog.require('grrUi.client.clientStatsViewDirective.ClientStatsViewDirective');
goog.require('grrUi.client.clientStatusIconsDirective.ClientStatusIconsDirective');
goog.require('grrUi.client.clientUsernamesDirective.ClientUsernamesDirective');
goog.require('grrUi.client.clientsListDirective.ClientsListDirective');
goog.require('grrUi.client.debugRequestsViewDirective.DebugRequestsViewDirective');
goog.require('grrUi.client.globalClientCrashesDirective.GlobalClientCrashesDirective');
goog.require('grrUi.client.hostInfoDirective.HostInfoDirective');
goog.require('grrUi.client.removeClientsLabelsDialogDirective.RemoveClientsLabelsDialogDirective');
goog.require('grrUi.client.virtualFileSystem.module');
goog.require('grrUi.core.module');
goog.require('grrUi.semantic.module');


/**
 * Angular module for clients-related UI.
 */
grrUi.client.module = angular.module('grrUi.client',
                                     [grrUi.client.virtualFileSystem.module.name,
                                      grrUi.core.module.name,
                                      grrUi.semantic.module.name]);

grrUi.client.module.directive(
    grrUi.client.addClientsLabelsDialogDirective.AddClientsLabelsDialogDirective
        .directive_name,
    grrUi.client.addClientsLabelsDialogDirective
        .AddClientsLabelsDialogDirective);
grrUi.client.module.directive(
    grrUi.client.clientCrashesDirective.ClientCrashesDirective.directive_name,
    grrUi.client.clientCrashesDirective.ClientCrashesDirective);
grrUi.client.module.directive(
    grrUi.client.clientsListDirective.ClientsListDirective.directive_name,
    grrUi.client.clientsListDirective.ClientsListDirective);
grrUi.client.module.directive(
    grrUi.client.clientLoadViewDirective.ClientLoadViewDirective.directive_name,
    grrUi.client.clientLoadViewDirective.ClientLoadViewDirective);
grrUi.client.module.directive(
    grrUi.client.clientStatusIconsDirective.ClientStatusIconsDirective
        .directive_name,
    grrUi.client.clientStatusIconsDirective.ClientStatusIconsDirective);
grrUi.client.module.directive(
    grrUi.client.clientUsernamesDirective.ClientUsernamesDirective
        .directive_name,
    grrUi.client.clientUsernamesDirective.ClientUsernamesDirective);
grrUi.client.module.directive(
    grrUi.client.debugRequestsViewDirective.DebugRequestsViewDirective.directive_name,
    grrUi.client.debugRequestsViewDirective.DebugRequestsViewDirective);
grrUi.client.module.directive(
    grrUi.client.globalClientCrashesDirective.GlobalClientCrashesDirective.directive_name,
    grrUi.client.globalClientCrashesDirective.GlobalClientCrashesDirective);
grrUi.client.module.directive(
    grrUi.client.hostInfoDirective.HostInfoDirective.directive_name,
    grrUi.client.hostInfoDirective.HostInfoDirective);
grrUi.client.module.directive(
    grrUi.client.removeClientsLabelsDialogDirective
        .RemoveClientsLabelsDialogDirective.directive_name,
    grrUi.client.removeClientsLabelsDialogDirective
        .RemoveClientsLabelsDialogDirective);
grrUi.client.module.directive(
    grrUi.client.clientStatsViewDirective.ClientStatsViewDirective.directive_name,
    grrUi.client.clientStatsViewDirective.ClientStatsViewDirective);

grrUi.core.module.service(
    grrUi.client.clientDialogService.ClientDialogService.service_name,
    grrUi.client.clientDialogService.ClientDialogService);
