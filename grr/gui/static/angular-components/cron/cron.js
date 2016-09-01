'use strict';

goog.provide('grrUi.cron.module');

goog.require('grrUi.core.module');

goog.require('grrUi.cron.cronJobFlowsListDirective.CronJobFlowsListDirective');
goog.require('grrUi.cron.cronJobInspectorDirective.CronJobInspectorDirective');
goog.require('grrUi.cron.cronJobOverviewDirective.CronJobOverviewDirective');
goog.require('grrUi.cron.cronJobStatusIconDirective.CronJobStatusIconDirective');
goog.require('grrUi.cron.cronJobsListDirective.CronJobsListDirective');
goog.require('grrUi.cron.cronViewDirective.CronViewDirective');
goog.require('grrUi.cron.newCronJobWizard.module');


/**
 * Angular module for cron-related UI.
 */
grrUi.cron.module = angular.module('grrUi.cron',
                                   [grrUi.core.module.name,
                                    grrUi.cron.newCronJobWizard.module.name]);

grrUi.cron.module.directive(
    grrUi.cron.cronJobFlowsListDirective.CronJobFlowsListDirective.directive_name,
    grrUi.cron.cronJobFlowsListDirective.CronJobFlowsListDirective);
grrUi.cron.module.directive(
    grrUi.cron.cronJobInspectorDirective.CronJobInspectorDirective.
        directive_name,
    grrUi.cron.cronJobInspectorDirective.CronJobInspectorDirective);
grrUi.cron.module.directive(
    grrUi.cron.cronJobsListDirective.CronJobsListDirective.directive_name,
    grrUi.cron.cronJobsListDirective.CronJobsListDirective);
grrUi.cron.module.directive(
    grrUi.cron.cronJobOverviewDirective.CronJobOverviewDirective.
        directive_name,
    grrUi.cron.cronJobOverviewDirective.CronJobOverviewDirective);
grrUi.cron.module.directive(
    grrUi.cron.cronJobStatusIconDirective.CronJobStatusIconDirective
        .directive_name,
    grrUi.cron.cronJobStatusIconDirective.CronJobStatusIconDirective);
grrUi.cron.module.directive(
    grrUi.cron.cronViewDirective.CronViewDirective.directive_name,
    grrUi.cron.cronViewDirective.CronViewDirective);
