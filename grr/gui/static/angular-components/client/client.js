'use strict';

goog.provide('grrUi.client');
goog.provide('grrUi.client.clientModule');
goog.require('grrUi.client.addClientsLabelsDialogDirective');  // USE: AddClientsLabelsDialogDirective
goog.require('grrUi.client.checkClientAccessDirective');  // USE: CheckClientAccessDirective
goog.require('grrUi.client.clientContextDirective');  // USE: ClientContextDirective
goog.require('grrUi.client.clientCrashesDirective');  // USE: ClientCrashesDirective
goog.require('grrUi.client.clientDialogService');  // USE: ClientDialogService
goog.require('grrUi.client.clientLoadGraphSerieDirective');  // USE: ClientLoadGraphSerieDirective
goog.require('grrUi.client.clientLoadViewDirective');  // USE: ClientLoadViewDirective
goog.require('grrUi.client.clientStatusIconsDirective');  // USE: ClientStatusIconsDirective
goog.require('grrUi.client.clientUsernamesDirective');  // USE: ClientUsernamesDirective
goog.require('grrUi.client.clientsListDirective');  // USE: ClientsListDirective
goog.require('grrUi.client.debugRequestsViewDirective');  // USE: DebugRequestsViewDirective
goog.require('grrUi.client.hostHistoryDialogDirective');  // USE: HostHistoryDialogDirective
goog.require('grrUi.client.hostInfoDirective');  // USE: HostInfoDirective
goog.require('grrUi.client.removeClientsLabelsDialogDirective');  // USE: RemoveClientsLabelsDialogDirective
goog.require('grrUi.client.virtualFileSystem');  // USE: virtualFileSystemModule
goog.require('grrUi.core');                      // USE: coreModule
goog.require('grrUi.semantic');                  // USE: semanticModule
goog.require('grrUi.stats');                     // USE: statsModule


/**
 * Angular module for clients-related UI.
 */
grrUi.client.clientModule = angular.module('grrUi.client',
                                     [grrUi.client.virtualFileSystem.virtualFileSystemModule.name,
                                      grrUi.core.coreModule.name,
                                      grrUi.semantic.semanticModule.name,
                                      grrUi.stats.statsModule.name
                                     ]);

grrUi.client.clientModule.directive(
    grrUi.client.addClientsLabelsDialogDirective.AddClientsLabelsDialogDirective
        .directive_name,
    grrUi.client.addClientsLabelsDialogDirective
        .AddClientsLabelsDialogDirective);
grrUi.client.clientModule.directive(
    grrUi.client.checkClientAccessDirective.CheckClientAccessDirective.directive_name,
    grrUi.client.checkClientAccessDirective.CheckClientAccessDirective);
grrUi.client.clientModule.directive(
    grrUi.client.clientContextDirective.ClientContextDirective.directive_name,
    grrUi.client.clientContextDirective.ClientContextDirective);
grrUi.client.clientModule.directive(
    grrUi.client.clientCrashesDirective.ClientCrashesDirective.directive_name,
    grrUi.client.clientCrashesDirective.ClientCrashesDirective);
grrUi.client.clientModule.directive(
    grrUi.client.clientsListDirective.ClientsListDirective.directive_name,
    grrUi.client.clientsListDirective.ClientsListDirective);
grrUi.client.clientModule.directive(
    grrUi.client.clientLoadGraphSerieDirective.ClientLoadGraphSerieDirective
        .directive_name,
    grrUi.client.clientLoadGraphSerieDirective.ClientLoadGraphSerieDirective);
grrUi.client.clientModule.directive(
    grrUi.client.clientLoadViewDirective.ClientLoadViewDirective.directive_name,
    grrUi.client.clientLoadViewDirective.ClientLoadViewDirective);
grrUi.client.clientModule.directive(
    grrUi.client.clientStatusIconsDirective.ClientStatusIconsDirective
        .directive_name,
    grrUi.client.clientStatusIconsDirective.ClientStatusIconsDirective);
grrUi.client.clientModule.directive(
    grrUi.client.clientUsernamesDirective.ClientUsernamesDirective
        .directive_name,
    grrUi.client.clientUsernamesDirective.ClientUsernamesDirective);
grrUi.client.clientModule.directive(
    grrUi.client.debugRequestsViewDirective.DebugRequestsViewDirective.directive_name,
    grrUi.client.debugRequestsViewDirective.DebugRequestsViewDirective);
grrUi.client.clientModule.directive(
    grrUi.client.hostHistoryDialogDirective.HostHistoryDialogDirective.directive_name,
    grrUi.client.hostHistoryDialogDirective.HostHistoryDialogDirective);
grrUi.client.clientModule.directive(
    grrUi.client.hostInfoDirective.HostInfoDirective.directive_name,
    grrUi.client.hostInfoDirective.HostInfoDirective);
grrUi.client.clientModule.directive(
    grrUi.client.removeClientsLabelsDialogDirective
        .RemoveClientsLabelsDialogDirective.directive_name,
    grrUi.client.removeClientsLabelsDialogDirective
        .RemoveClientsLabelsDialogDirective);

grrUi.client.clientModule.service(
    grrUi.client.clientDialogService.ClientDialogService.service_name,
    grrUi.client.clientDialogService.ClientDialogService);
