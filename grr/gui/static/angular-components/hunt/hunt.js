'use strict';

goog.provide('grrUi.hunt.module');

goog.require('grrUi.core.module');

goog.require('grrUi.hunt.huntContextDirective.HuntContextDirective');
goog.require('grrUi.hunt.huntCrashesDirective.HuntCrashesDirective');
goog.require('grrUi.hunt.huntDetailsDirective.HuntDetailsDirective');
goog.require('grrUi.hunt.huntErrorsDirective.HuntErrorsDirective');
goog.require('grrUi.hunt.huntGraphDirective.HuntGraphDirective');
goog.require('grrUi.hunt.huntInspectorDirective.HuntInspectorDirective');
goog.require('grrUi.hunt.huntLogDirective.HuntLogDirective');
goog.require('grrUi.hunt.huntOutstandingClientsDirective.HuntOutstandingClientsDirective');
goog.require('grrUi.hunt.huntOverviewDirective.HuntOverviewDirective');
goog.require('grrUi.hunt.huntResultsDirective.HuntResultsDirective');
goog.require('grrUi.hunt.huntStatsDirective.HuntStatsDirective');
goog.require('grrUi.hunt.huntStatusIconDirective.HuntStatusIconDirective');
goog.require('grrUi.hunt.huntsListDirective.HuntsListDirective');
goog.require('grrUi.hunt.huntsViewDirective.HuntsViewDirective');

goog.require('grrUi.hunt.newHuntWizard.module');


/**
 * Angular module for hunts-related UI.
 */
grrUi.hunt.module = angular.module('grrUi.hunt',
                                   ['ui.bootstrap',
                                    grrUi.core.module.name,
                                    grrUi.hunt.newHuntWizard.module.name]);


grrUi.hunt.module.directive(
    grrUi.hunt.huntContextDirective.HuntContextDirective.directive_name,
    grrUi.hunt.huntContextDirective.HuntContextDirective);
grrUi.hunt.module.directive(
    grrUi.hunt.huntCrashesDirective.HuntCrashesDirective.directive_name,
    grrUi.hunt.huntCrashesDirective.HuntCrashesDirective);
grrUi.hunt.module.directive(
    grrUi.hunt.huntDetailsDirective.HuntDetailsDirective.directive_name,
    grrUi.hunt.huntDetailsDirective.HuntDetailsDirective);
grrUi.hunt.module.directive(
    grrUi.hunt.huntErrorsDirective.HuntErrorsDirective.directive_name,
    grrUi.hunt.huntErrorsDirective.HuntErrorsDirective);
grrUi.hunt.module.directive(
    grrUi.hunt.huntGraphDirective.HuntGraphDirective.directive_name,
    grrUi.hunt.huntGraphDirective.HuntGraphDirective);
grrUi.hunt.module.directive(
    grrUi.hunt.huntInspectorDirective.HuntInspectorDirective.directive_name,
    grrUi.hunt.huntInspectorDirective.HuntInspectorDirective);
grrUi.hunt.module.directive(
    grrUi.hunt.huntLogDirective.HuntLogDirective.directive_name,
    grrUi.hunt.huntLogDirective.HuntLogDirective);
grrUi.hunt.module.directive(
    grrUi.hunt.huntOverviewDirective.HuntOverviewDirective.directive_name,
    grrUi.hunt.huntOverviewDirective.HuntOverviewDirective);
grrUi.hunt.module.directive(
    grrUi.hunt.huntOutstandingClientsDirective.HuntOutstandingClientsDirective.directive_name,
    grrUi.hunt.huntOutstandingClientsDirective.HuntOutstandingClientsDirective);
grrUi.hunt.module.directive(
    grrUi.hunt.huntResultsDirective.HuntResultsDirective.directive_name,
    grrUi.hunt.huntResultsDirective.HuntResultsDirective);
grrUi.hunt.module.directive(
    grrUi.hunt.huntStatusIconDirective.HuntStatusIconDirective.directive_name,
    grrUi.hunt.huntStatusIconDirective.HuntStatusIconDirective);
grrUi.hunt.module.directive(
    grrUi.hunt.huntStatsDirective.HuntStatsDirective.directive_name,
    grrUi.hunt.huntStatsDirective.HuntStatsDirective);
grrUi.hunt.module.directive(
    grrUi.hunt.huntsListDirective.HuntsListDirective.directive_name,
    grrUi.hunt.huntsListDirective.HuntsListDirective);
grrUi.hunt.module.directive(
    grrUi.hunt.huntsViewDirective.HuntsViewDirective.directive_name,
    grrUi.hunt.huntsViewDirective.HuntsViewDirective);
