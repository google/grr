'use strict';

goog.provide('grrUi.hunt.huntModule');

goog.require('grrUi.core.coreModule');

goog.require('grrUi.hunt.huntClientsDirective.HuntClientsDirective');
goog.require('grrUi.hunt.huntContextDirective.HuntContextDirective');
goog.require('grrUi.hunt.huntCrashesDirective.HuntCrashesDirective');
goog.require('grrUi.hunt.huntErrorsDirective.HuntErrorsDirective');
goog.require('grrUi.hunt.huntGraphDirective.HuntGraphDirective');
goog.require('grrUi.hunt.huntInspectorDirective.HuntInspectorDirective');
goog.require('grrUi.hunt.huntLogDirective.HuntLogDirective');
goog.require('grrUi.hunt.huntOverviewDirective.HuntOverviewDirective');
goog.require('grrUi.hunt.huntResultsDirective.HuntResultsDirective');
goog.require('grrUi.hunt.huntStatsDirective.HuntStatsDirective');
goog.require('grrUi.hunt.huntStatusIconDirective.HuntStatusIconDirective');
goog.require('grrUi.hunt.huntsListDirective.HuntsListDirective');
goog.require('grrUi.hunt.huntsViewDirective.HuntsViewDirective');
goog.require('grrUi.hunt.modifyHuntDialogDirective.ModifyHuntDialogDirective');

goog.require('grrUi.hunt.newHuntWizard.newHuntWizardModule');


/**
 * Angular module for hunts-related UI.
 */
grrUi.hunt.huntModule = angular.module('grrUi.hunt',
                                   ['ui.bootstrap',
                                    grrUi.core.coreModule.name,
                                    grrUi.hunt.newHuntWizard.newHuntWizardModule.name]);


grrUi.hunt.huntModule.directive(
    grrUi.hunt.huntClientsDirective.HuntClientsDirective.directive_name,
    grrUi.hunt.huntClientsDirective.HuntClientsDirective);
grrUi.hunt.huntModule.directive(
    grrUi.hunt.huntContextDirective.HuntContextDirective.directive_name,
    grrUi.hunt.huntContextDirective.HuntContextDirective);
grrUi.hunt.huntModule.directive(
    grrUi.hunt.huntCrashesDirective.HuntCrashesDirective.directive_name,
    grrUi.hunt.huntCrashesDirective.HuntCrashesDirective);
grrUi.hunt.huntModule.directive(
    grrUi.hunt.huntErrorsDirective.HuntErrorsDirective.directive_name,
    grrUi.hunt.huntErrorsDirective.HuntErrorsDirective);
grrUi.hunt.huntModule.directive(
    grrUi.hunt.huntGraphDirective.HuntGraphDirective.directive_name,
    grrUi.hunt.huntGraphDirective.HuntGraphDirective);
grrUi.hunt.huntModule.directive(
    grrUi.hunt.huntInspectorDirective.HuntInspectorDirective.directive_name,
    grrUi.hunt.huntInspectorDirective.HuntInspectorDirective);
grrUi.hunt.huntModule.directive(
    grrUi.hunt.huntLogDirective.HuntLogDirective.directive_name,
    grrUi.hunt.huntLogDirective.HuntLogDirective);
grrUi.hunt.huntModule.directive(
    grrUi.hunt.huntOverviewDirective.HuntOverviewDirective.directive_name,
    grrUi.hunt.huntOverviewDirective.HuntOverviewDirective);
grrUi.hunt.huntModule.directive(
    grrUi.hunt.huntResultsDirective.HuntResultsDirective.directive_name,
    grrUi.hunt.huntResultsDirective.HuntResultsDirective);
grrUi.hunt.huntModule.directive(
    grrUi.hunt.huntStatusIconDirective.HuntStatusIconDirective.directive_name,
    grrUi.hunt.huntStatusIconDirective.HuntStatusIconDirective);
grrUi.hunt.huntModule.directive(
    grrUi.hunt.huntStatsDirective.HuntStatsDirective.directive_name,
    grrUi.hunt.huntStatsDirective.HuntStatsDirective);
grrUi.hunt.huntModule.directive(
    grrUi.hunt.huntsListDirective.HuntsListDirective.directive_name,
    grrUi.hunt.huntsListDirective.HuntsListDirective);
grrUi.hunt.huntModule.directive(
    grrUi.hunt.huntsViewDirective.HuntsViewDirective.directive_name,
    grrUi.hunt.huntsViewDirective.HuntsViewDirective);
grrUi.hunt.huntModule.directive(
    grrUi.hunt.modifyHuntDialogDirective.ModifyHuntDialogDirective
        .directive_name,
    grrUi.hunt.modifyHuntDialogDirective.ModifyHuntDialogDirective);
