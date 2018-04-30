'use strict';

goog.module('grrUi.cron.newCronJobWizard.statusPageDirective');
goog.module.declareLegacyNamespace();



/**
 * Directive for showing wizard-like forms with multiple named steps/pages.
 *
 * @return {!angular.Directive} Directive definition object.
 * @ngInject
 * @export
 */
exports.StatusPageDirective = function() {
  return {
    scope: {
      response: '=',
    },
    restrict: 'E',
    templateUrl: '/static/angular-components/cron/new-cron-job-wizard/' +
        'status-page.html'
  };
};


/**
 * Directive's name in Angular.
 *
 * @const
 * @export
 */
exports.StatusPageDirective.directive_name = 'grrNewCronJobStatusPage';
