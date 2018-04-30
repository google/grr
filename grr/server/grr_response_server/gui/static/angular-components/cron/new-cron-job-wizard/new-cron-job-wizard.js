'use strict';

goog.module('grrUi.cron.newCronJobWizard.newCronJobWizard');
goog.module.declareLegacyNamespace();

const {ConfigureSchedulePageDirective} = goog.require('grrUi.cron.newCronJobWizard.configureSchedulePageDirective');
const {FormDirective} = goog.require('grrUi.cron.newCronJobWizard.formDirective');
const {ReviewPageDirective} = goog.require('grrUi.cron.newCronJobWizard.reviewPageDirective');
const {StatusPageDirective} = goog.require('grrUi.cron.newCronJobWizard.statusPageDirective');
const {coreModule} = goog.require('grrUi.core.core');


/**
 * Angular module for new cron job wizard UI.
 */
exports.newCronJobWizardModule = angular.module(
    'grrUi.cron.newCronJobWizard', ['ui.bootstrap', coreModule.name]);

exports.newCronJobWizardModule.directive(
    FormDirective.directive_name, FormDirective);
exports.newCronJobWizardModule.directive(
    ReviewPageDirective.directive_name, ReviewPageDirective);
exports.newCronJobWizardModule.directive(
    StatusPageDirective.directive_name, StatusPageDirective);
exports.newCronJobWizardModule.directive(
    ConfigureSchedulePageDirective.directive_name,
    ConfigureSchedulePageDirective);
