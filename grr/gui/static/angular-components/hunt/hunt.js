'use strict';

goog.provide('grrUi.hunt.hunt');
goog.provide('grrUi.hunt.hunt.huntModule');

goog.require('grrUi.core.core');  // USE: coreModule

goog.require('grrUi.hunt.huntClientsDirective');    // USE: HuntClientsDirective
goog.require('grrUi.hunt.huntContextDirective');    // USE: HuntContextDirective
goog.require('grrUi.hunt.huntCrashesDirective');    // USE: HuntCrashesDirective
goog.require('grrUi.hunt.huntErrorsDirective');     // USE: HuntErrorsDirective
goog.require('grrUi.hunt.huntGraphDirective');      // USE: HuntGraphDirective
goog.require('grrUi.hunt.huntInspectorDirective');  // USE: HuntInspectorDirective
goog.require('grrUi.hunt.huntLogDirective');        // USE: HuntLogDirective
goog.require('grrUi.hunt.huntOverviewDirective');  // USE: HuntOverviewDirective
goog.require('grrUi.hunt.huntResultsDirective');   // USE: HuntResultsDirective
goog.require('grrUi.hunt.huntStatsDirective');     // USE: HuntStatsDirective
goog.require('grrUi.hunt.huntStatusIconDirective');  // USE: HuntStatusIconDirective
goog.require('grrUi.hunt.huntsListDirective');       // USE: HuntsListDirective
goog.require('grrUi.hunt.huntsViewDirective');       // USE: HuntsViewDirective
goog.require('grrUi.hunt.modifyHuntDialogDirective');  // USE: ModifyHuntDialogDirective

goog.require('grrUi.hunt.newHuntWizard.newHuntWizard');  // USE: newHuntWizardModule


/**
 * Angular module for hunts-related UI.
 */
grrUi.hunt.hunt.huntModule = angular.module('grrUi.hunt', [
  'ui.bootstrap', grrUi.core.core.coreModule.name,
  grrUi.hunt.newHuntWizard.newHuntWizard.newHuntWizardModule.name
]);


grrUi.hunt.hunt.huntModule.directive(
    grrUi.hunt.huntClientsDirective.HuntClientsDirective.directive_name,
    grrUi.hunt.huntClientsDirective.HuntClientsDirective);
grrUi.hunt.hunt.huntModule.directive(
    grrUi.hunt.huntContextDirective.HuntContextDirective.directive_name,
    grrUi.hunt.huntContextDirective.HuntContextDirective);
grrUi.hunt.hunt.huntModule.directive(
    grrUi.hunt.huntCrashesDirective.HuntCrashesDirective.directive_name,
    grrUi.hunt.huntCrashesDirective.HuntCrashesDirective);
grrUi.hunt.hunt.huntModule.directive(
    grrUi.hunt.huntErrorsDirective.HuntErrorsDirective.directive_name,
    grrUi.hunt.huntErrorsDirective.HuntErrorsDirective);
grrUi.hunt.hunt.huntModule.directive(
    grrUi.hunt.huntGraphDirective.HuntGraphDirective.directive_name,
    grrUi.hunt.huntGraphDirective.HuntGraphDirective);
grrUi.hunt.hunt.huntModule.directive(
    grrUi.hunt.huntInspectorDirective.HuntInspectorDirective.directive_name,
    grrUi.hunt.huntInspectorDirective.HuntInspectorDirective);
grrUi.hunt.hunt.huntModule.directive(
    grrUi.hunt.huntLogDirective.HuntLogDirective.directive_name,
    grrUi.hunt.huntLogDirective.HuntLogDirective);
grrUi.hunt.hunt.huntModule.directive(
    grrUi.hunt.huntOverviewDirective.HuntOverviewDirective.directive_name,
    grrUi.hunt.huntOverviewDirective.HuntOverviewDirective);
grrUi.hunt.hunt.huntModule.directive(
    grrUi.hunt.huntResultsDirective.HuntResultsDirective.directive_name,
    grrUi.hunt.huntResultsDirective.HuntResultsDirective);
grrUi.hunt.hunt.huntModule.directive(
    grrUi.hunt.huntStatusIconDirective.HuntStatusIconDirective.directive_name,
    grrUi.hunt.huntStatusIconDirective.HuntStatusIconDirective);
grrUi.hunt.hunt.huntModule.directive(
    grrUi.hunt.huntStatsDirective.HuntStatsDirective.directive_name,
    grrUi.hunt.huntStatsDirective.HuntStatsDirective);
grrUi.hunt.hunt.huntModule.directive(
    grrUi.hunt.huntsListDirective.HuntsListDirective.directive_name,
    grrUi.hunt.huntsListDirective.HuntsListDirective);
grrUi.hunt.hunt.huntModule.directive(
    grrUi.hunt.huntsViewDirective.HuntsViewDirective.directive_name,
    grrUi.hunt.huntsViewDirective.HuntsViewDirective);
grrUi.hunt.hunt.huntModule.directive(
    grrUi.hunt.modifyHuntDialogDirective.ModifyHuntDialogDirective
        .directive_name,
    grrUi.hunt.modifyHuntDialogDirective.ModifyHuntDialogDirective);
