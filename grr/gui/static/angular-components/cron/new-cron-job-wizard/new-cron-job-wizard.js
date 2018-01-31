goog.provide('grrUi.cron.newCronJobWizard');
goog.provide('grrUi.cron.newCronJobWizard.newCronJobWizardModule');

goog.require('grrUi.core.coreModule');

goog.require('grrUi.cron.newCronJobWizard.configureSchedulePageDirective.ConfigureSchedulePageDirective');
goog.require('grrUi.cron.newCronJobWizard.formDirective.FormDirective');
goog.require('grrUi.cron.newCronJobWizard.reviewPageDirective.ReviewPageDirective');
goog.require('grrUi.cron.newCronJobWizard.statusPageDirective.StatusPageDirective');


/**
 * Angular module for new cron job wizard UI.
 */
grrUi.cron.newCronJobWizard.newCronJobWizardModule = angular.module(
    'grrUi.cron.newCronJobWizard',
    ['ui.bootstrap', grrUi.core.coreModule.name]);

grrUi.cron.newCronJobWizard.newCronJobWizardModule.directive(
    grrUi.cron.newCronJobWizard.formDirective.FormDirective.directive_name,
    grrUi.cron.newCronJobWizard.formDirective.FormDirective);
grrUi.cron.newCronJobWizard.newCronJobWizardModule.directive(
    grrUi.cron.newCronJobWizard.reviewPageDirective
        .ReviewPageDirective.directive_name,
    grrUi.cron.newCronJobWizard.reviewPageDirective.ReviewPageDirective);
grrUi.cron.newCronJobWizard.newCronJobWizardModule.directive(
    grrUi.cron.newCronJobWizard.statusPageDirective
        .StatusPageDirective.directive_name,
    grrUi.cron.newCronJobWizard.statusPageDirective.StatusPageDirective);
grrUi.cron.newCronJobWizard.newCronJobWizardModule.directive(
    grrUi.cron.newCronJobWizard.configureSchedulePageDirective
        .ConfigureSchedulePageDirective.directive_name,
    grrUi.cron.newCronJobWizard.configureSchedulePageDirective
        .ConfigureSchedulePageDirective);
