'use strict';

goog.provide('grrUi.cron.newCronJobDeprecatedWizard.configureSchedulePageDirective.ConfigureSchedulePageDirective');

goog.scope(function() {

/**
 * Directive for showing wizard-like forms with multiple named steps/pages.
 *
 * @constructor
 * @ngInject
 * @export
 */
grrUi.cron.newCronJobDeprecatedWizard.configureSchedulePageDirective
    .ConfigureSchedulePageDirective = function() {
  return {
    scope: {
      cronJob: '='
    },
    restrict: 'E',
    templateUrl: '/static/angular-components/cron/' +
        'new-cron-job-deprecated-wizard/configure-schedule-page.html',
    controllerAs: 'controller'
  };
};


/**
 * Directive's name in Angular.
 *
 * @const
 * @export
 */
grrUi.cron.newCronJobDeprecatedWizard.configureSchedulePageDirective
    .ConfigureSchedulePageDirective
    .directive_name = 'grrConfigureDeprecatedSchedulePage';

});  // goog.scope
