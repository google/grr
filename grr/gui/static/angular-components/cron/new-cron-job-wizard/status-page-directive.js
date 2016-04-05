'use strict';

goog.provide('grrUi.cron.newCronJobWizard.statusPageDirective.StatusPageDirective');

goog.scope(function() {

/**
 * Directive for showing wizard-like forms with multiple named steps/pages.
 *
 * @constructor
 * @ngInject
 * @export
 */
grrUi.cron.newCronJobWizard.statusPageDirective.StatusPageDirective =
    function() {
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
grrUi.cron.newCronJobWizard.statusPageDirective.StatusPageDirective
    .directive_name = 'grrNewCronJobStatusPage';

});  // goog.scope
