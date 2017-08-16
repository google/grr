'use strict';

goog.provide('grrUi.client.module');
goog.require('grrUi.client.addClientsLabelsDialogDirective.AddClientsLabelsDialogDirective');
goog.require('grrUi.client.checkClientAccessDirective.CheckClientAccessDirective');
goog.require('grrUi.client.clientContextDirective.ClientContextDirective');
goog.require('grrUi.client.clientCrashesDirective.ClientCrashesDirective');
goog.require('grrUi.client.clientDialogService.ClientDialogService');
goog.require('grrUi.client.clientLoadGraphSerieDirective.ClientLoadGraphSerieDirective');
goog.require('grrUi.client.clientLoadViewDirective.ClientLoadViewDirective');
goog.require('grrUi.client.clientStatusIconsDirective.ClientStatusIconsDirective');
goog.require('grrUi.client.clientUsernamesDirective.ClientUsernamesDirective');
goog.require('grrUi.client.clientsListDirective.ClientsListDirective');
goog.require('grrUi.client.debugRequestsViewDirective.DebugRequestsViewDirective');
goog.require('grrUi.client.hostHistoryDialogDirective.HostHistoryDialogDirective');
goog.require('grrUi.client.hostInfoDirective.HostInfoDirective');
goog.require('grrUi.client.removeClientsLabelsDialogDirective.RemoveClientsLabelsDialogDirective');
goog.require('grrUi.client.virtualFileSystem.module');
goog.require('grrUi.core.module');
goog.require('grrUi.semantic.module');
goog.require('grrUi.stats.module');


/**
 * Angular module for clients-related UI.
 */
grrUi.client.module = angular.module('grrUi.client',
                                     [grrUi.client.virtualFileSystem.module.name,
                                      grrUi.core.module.name,
                                      grrUi.semantic.module.name,
                                      grrUi.stats.module.name
                                     ]);

grrUi.client.module.directive(
    grrUi.client.addClientsLabelsDialogDirective.AddClientsLabelsDialogDirective
        .directive_name,
    grrUi.client.addClientsLabelsDialogDirective
        .AddClientsLabelsDialogDirective);
grrUi.client.module.directive(
    grrUi.client.checkClientAccessDirective.CheckClientAccessDirective.directive_name,
    grrUi.client.checkClientAccessDirective.CheckClientAccessDirective);
grrUi.client.module.directive(
    grrUi.client.clientContextDirective.ClientContextDirective.directive_name,
    grrUi.client.clientContextDirective.ClientContextDirective);
grrUi.client.module.directive(
    grrUi.client.clientCrashesDirective.ClientCrashesDirective.directive_name,
    grrUi.client.clientCrashesDirective.ClientCrashesDirective);
grrUi.client.module.directive(
    grrUi.client.clientsListDirective.ClientsListDirective.directive_name,
    grrUi.client.clientsListDirective.ClientsListDirective);
grrUi.client.module.directive(
    grrUi.client.clientLoadGraphSerieDirective.ClientLoadGraphSerieDirective
        .directive_name,
    grrUi.client.clientLoadGraphSerieDirective.ClientLoadGraphSerieDirective);
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
    grrUi.client.hostHistoryDialogDirective.HostHistoryDialogDirective.directive_name,
    grrUi.client.hostHistoryDialogDirective.HostHistoryDialogDirective);
grrUi.client.module.directive(
    grrUi.client.hostInfoDirective.HostInfoDirective.directive_name,
    grrUi.client.hostInfoDirective.HostInfoDirective);
grrUi.client.module.directive(
    grrUi.client.removeClientsLabelsDialogDirective
        .RemoveClientsLabelsDialogDirective.directive_name,
    grrUi.client.removeClientsLabelsDialogDirective
        .RemoveClientsLabelsDialogDirective);

grrUi.core.module.service(
    grrUi.client.clientDialogService.ClientDialogService.service_name,
    grrUi.client.clientDialogService.ClientDialogService);
