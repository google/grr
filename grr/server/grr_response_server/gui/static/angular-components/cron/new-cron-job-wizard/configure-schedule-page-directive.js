'use strict';

goog.module('grrUi.cron.newCronJobWizard.configureSchedulePageDirective');
goog.module.declareLegacyNamespace();



/**
 * Directive for showing wizard-like forms with multiple named steps/pages.
 *
 * @return {!angular.Directive} Directive definition object.
 * @ngInject
 * @export
 */
exports.ConfigureSchedulePageDirective = function() {
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
exports.ConfigureSchedulePageDirective.directive_name =
    'grrConfigureSchedulePage';
