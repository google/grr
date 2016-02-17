goog.provide('grrUi.cron.newCronJobDeprecatedWizard.module');

goog.require('grrUi.core.module');

goog.require('grrUi.cron.newCronJobDeprecatedWizard.configureSchedulePageDirective.ConfigureSchedulePageDirective');
goog.require('grrUi.cron.newCronJobDeprecatedWizard.formDirective.FormDirective');
goog.require('grrUi.cron.newCronJobDeprecatedWizard.reviewPageDirective.ReviewPageDirective');
goog.require('grrUi.cron.newCronJobDeprecatedWizard.statusPageDirective.StatusPageDirective');


/**
 * Angular module for new cron job deprecated wizard UI.
 */
grrUi.cron.newCronJobDeprecatedWizard.module = angular.module(
    'grrUi.cron.newCronJobDeprecatedWizard',
    ['ui.bootstrap', grrUi.core.module.name]);

grrUi.cron.newCronJobDeprecatedWizard.module.directive(
    grrUi.cron.newCronJobDeprecatedWizard.formDirective.FormDirective.directive_name,
    grrUi.cron.newCronJobDeprecatedWizard.formDirective.FormDirective);
grrUi.cron.newCronJobDeprecatedWizard.module.directive(
    grrUi.cron.newCronJobDeprecatedWizard.reviewPageDirective
        .ReviewPageDirective.directive_name,
    grrUi.cron.newCronJobDeprecatedWizard.reviewPageDirective.ReviewPageDirective);
grrUi.cron.newCronJobDeprecatedWizard.module.directive(
    grrUi.cron.newCronJobDeprecatedWizard.statusPageDirective
        .StatusPageDirective.directive_name,
    grrUi.cron.newCronJobDeprecatedWizard.statusPageDirective.StatusPageDirective);
grrUi.cron.newCronJobDeprecatedWizard.module.directive(
    grrUi.cron.newCronJobDeprecatedWizard.configureSchedulePageDirective
        .ConfigureSchedulePageDirective.directive_name,
    grrUi.cron.newCronJobDeprecatedWizard.configureSchedulePageDirective
        .ConfigureSchedulePageDirective);
