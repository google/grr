'use strict';

goog.module('grrUi.client.client');
goog.module.declareLegacyNamespace();

const {AddClientsLabelsDialogDirective} = goog.require('grrUi.client.addClientsLabelsDialogDirective');
const {CheckClientAccessDirective} = goog.require('grrUi.client.checkClientAccessDirective');
const {ClientContextDirective} = goog.require('grrUi.client.clientContextDirective');
const {ClientCrashesDirective} = goog.require('grrUi.client.clientCrashesDirective');
const {ClientDialogService} = goog.require('grrUi.client.clientDialogService');
const {ClientLoadGraphSerieDirective} = goog.require('grrUi.client.clientLoadGraphSerieDirective');
const {ClientLoadViewDirective} = goog.require('grrUi.client.clientLoadViewDirective');
const {ClientStatusIconsDirective} = goog.require('grrUi.client.clientStatusIconsDirective');
const {ClientUsernamesDirective} = goog.require('grrUi.client.clientUsernamesDirective');
const {ClientsListDirective} = goog.require('grrUi.client.clientsListDirective');
const {DebugRequestsViewDirective} = goog.require('grrUi.client.debugRequestsViewDirective');
const {HostHistoryDialogDirective} = goog.require('grrUi.client.hostHistoryDialogDirective');
const {HostInfoDirective} = goog.require('grrUi.client.hostInfoDirective');
const {RemoveClientsLabelsDialogDirective} = goog.require('grrUi.client.removeClientsLabelsDialogDirective');
const {coreModule} = goog.require('grrUi.core.core');
const {semanticModule} = goog.require('grrUi.semantic.semantic');
const {statsModule} = goog.require('grrUi.stats.stats');
const {virtualFileSystemModule} = goog.require('grrUi.client.virtualFileSystem.virtualFileSystem');


/**
 * Angular module for clients-related UI.
 */
exports.clientModule = angular.module('grrUi.client', [
  virtualFileSystemModule.name, coreModule.name, semanticModule.name,
  statsModule.name
]);

exports.clientModule.directive(
    AddClientsLabelsDialogDirective.directive_name,
    AddClientsLabelsDialogDirective);
exports.clientModule.directive(
    CheckClientAccessDirective.directive_name, CheckClientAccessDirective);
exports.clientModule.directive(
    ClientContextDirective.directive_name, ClientContextDirective);
exports.clientModule.directive(
    ClientCrashesDirective.directive_name, ClientCrashesDirective);
exports.clientModule.directive(
    ClientsListDirective.directive_name, ClientsListDirective);
exports.clientModule.directive(
    ClientLoadGraphSerieDirective.directive_name,
    ClientLoadGraphSerieDirective);
exports.clientModule.directive(
    ClientLoadViewDirective.directive_name, ClientLoadViewDirective);
exports.clientModule.directive(
    ClientStatusIconsDirective.directive_name, ClientStatusIconsDirective);
exports.clientModule.directive(
    ClientUsernamesDirective.directive_name, ClientUsernamesDirective);
exports.clientModule.directive(
    DebugRequestsViewDirective.directive_name, DebugRequestsViewDirective);
exports.clientModule.directive(
    HostHistoryDialogDirective.directive_name, HostHistoryDialogDirective);
exports.clientModule.directive(
    HostInfoDirective.directive_name, HostInfoDirective);
exports.clientModule.directive(
    RemoveClientsLabelsDialogDirective.directive_name,
    RemoveClientsLabelsDialogDirective);

exports.clientModule.service(
    ClientDialogService.service_name, ClientDialogService);
