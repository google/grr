'use strict';

goog.provide('grrUi.cron.newCronJobWizard.configureSchedulePageDirective.ConfigureSchedulePageDirective');

goog.scope(function() {

/**
 * Directive for showing wizard-like forms with multiple named steps/pages.
 *
 * @constructor
 * @ngInject
 * @export
 */
grrUi.cron.newCronJobWizard.configureSchedulePageDirective
    .ConfigureSchedulePageDirective = function() {
  return {
    scope: {
      cronJob: '='
    },
    restrict: 'E',
    templateUrl: '/static/angular-components/cron/new-cron-job-wizard/' +
        'configure-schedule-page.html',
    controllerAs: 'controller'
  };
};


/**
 * Directive's name in Angular.
 *
 * @const
 * @export
 */
grrUi.cron.newCronJobWizard.configureSchedulePageDirective
    .ConfigureSchedulePageDirective
    .directive_name = 'grrConfigureSchedulePage';

});  // goog.scope
