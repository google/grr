'use strict';

goog.provide('grrUi.cron');
goog.provide('grrUi.cron.cronModule');

goog.require('grrUi.core.coreModule');

goog.require('grrUi.cron.cronJobFlowsListDirective.CronJobFlowsListDirective');
goog.require('grrUi.cron.cronJobInspectorDirective.CronJobInspectorDirective');
goog.require('grrUi.cron.cronJobOverviewDirective.CronJobOverviewDirective');
goog.require('grrUi.cron.cronJobStatusIconDirective.CronJobStatusIconDirective');
goog.require('grrUi.cron.cronJobsListDirective.CronJobsListDirective');
goog.require('grrUi.cron.cronViewDirective.CronViewDirective');
goog.require('grrUi.cron.newCronJobWizard.newCronJobWizardModule');


/**
 * Angular module for cron-related UI.
 */
grrUi.cron.cronModule = angular.module('grrUi.cron',
                                   [grrUi.core.coreModule.name,
                                    grrUi.cron.newCronJobWizard.newCronJobWizardModule.name]);

grrUi.cron.cronModule.directive(
    grrUi.cron.cronJobFlowsListDirective.CronJobFlowsListDirective.directive_name,
    grrUi.cron.cronJobFlowsListDirective.CronJobFlowsListDirective);
grrUi.cron.cronModule.directive(
    grrUi.cron.cronJobInspectorDirective.CronJobInspectorDirective.
        directive_name,
    grrUi.cron.cronJobInspectorDirective.CronJobInspectorDirective);
grrUi.cron.cronModule.directive(
    grrUi.cron.cronJobsListDirective.CronJobsListDirective.directive_name,
    grrUi.cron.cronJobsListDirective.CronJobsListDirective);
grrUi.cron.cronModule.directive(
    grrUi.cron.cronJobOverviewDirective.CronJobOverviewDirective.
        directive_name,
    grrUi.cron.cronJobOverviewDirective.CronJobOverviewDirective);
grrUi.cron.cronModule.directive(
    grrUi.cron.cronJobStatusIconDirective.CronJobStatusIconDirective
        .directive_name,
    grrUi.cron.cronJobStatusIconDirective.CronJobStatusIconDirective);
grrUi.cron.cronModule.directive(
    grrUi.cron.cronViewDirective.CronViewDirective.directive_name,
    grrUi.cron.cronViewDirective.CronViewDirective);
