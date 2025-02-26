goog.module('grrUi.cron.cron');

const {CronJobInspectorDirective} = goog.require('grrUi.cron.cronJobInspectorDirective');
const {CronJobOverviewDirective} = goog.require('grrUi.cron.cronJobOverviewDirective');
const {CronJobRunsListDirective} = goog.require('grrUi.cron.cronJobRunsListDirective');
const {CronJobStatusIconDirective} = goog.require('grrUi.cron.cronJobStatusIconDirective');
const {CronJobsListDirective} = goog.require('grrUi.cron.cronJobsListDirective');
const {CronViewDirective} = goog.require('grrUi.cron.cronViewDirective');
const {coreModule} = goog.require('grrUi.core.core');
const {newCronJobWizardModule} = goog.require('grrUi.cron.newCronJobWizard.newCronJobWizard');


/**
 * Angular module for cron-related UI.
 */
exports.cronModule = angular.module(
    'grrUi.cron', [coreModule.name, newCronJobWizardModule.name]);

exports.cronModule.directive(
    CronJobInspectorDirective.directive_name, CronJobInspectorDirective);
exports.cronModule.directive(
    CronJobsListDirective.directive_name, CronJobsListDirective);
exports.cronModule.directive(
    CronJobOverviewDirective.directive_name, CronJobOverviewDirective);
exports.cronModule.directive(
    CronJobRunsListDirective.directive_name, CronJobRunsListDirective);
exports.cronModule.directive(
    CronJobStatusIconDirective.directive_name, CronJobStatusIconDirective);
exports.cronModule.directive(
    CronViewDirective.directive_name, CronViewDirective);
