'use strict';

goog.provide('grrUi.hunt.module');

goog.require('grrUi.core.module');
goog.require('grrUi.hunt.huntCrashesDirective.HuntCrashesDirective');
goog.require('grrUi.hunt.huntErrorsDirective.HuntErrorsDirective');
goog.require('grrUi.hunt.huntInspectorDirective.HuntInspectorDirective');
goog.require('grrUi.hunt.huntLogDirective.HuntLogDirective');
goog.require('grrUi.hunt.huntOverviewDirective.HuntOverviewDirective');
goog.require('grrUi.hunt.huntResultsDirective.HuntResultsDirective');
goog.require('grrUi.hunt.huntsListDirective.HuntsListDirective');
goog.require('grrUi.hunt.huntsViewDirective.HuntsViewDirective');


/**
 * Angular module for hunts-related UI.
 */
grrUi.hunt.module = angular.module('grrUi.hunt', [grrUi.core.module.name]);


grrUi.hunt.module.directive(
    grrUi.hunt.huntCrashesDirective.HuntCrashesDirective.directive_name,
    grrUi.hunt.huntCrashesDirective.HuntCrashesDirective);
grrUi.hunt.module.directive(
    grrUi.hunt.huntErrorsDirective.HuntErrorsDirective.directive_name,
    grrUi.hunt.huntErrorsDirective.HuntErrorsDirective);
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
    grrUi.hunt.huntResultsDirective.HuntResultsDirective.directive_name,
    grrUi.hunt.huntResultsDirective.HuntResultsDirective);
grrUi.hunt.module.directive(
    grrUi.hunt.huntsListDirective.HuntsListDirective.directive_name,
    grrUi.hunt.huntsListDirective.HuntsListDirective);
grrUi.hunt.module.directive(
    grrUi.hunt.huntsViewDirective.HuntsViewDirective.directive_name,
    grrUi.hunt.huntsViewDirective.HuntsViewDirective);
