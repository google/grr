'use strict';

goog.provide('grrUi.cron.newCronJobDeprecatedWizard.statusPageDirective.StatusPageDirective');

goog.scope(function() {

/**
 * Directive for showing wizard-like forms with multiple named steps/pages.
 *
 * @constructor
 * @ngInject
 * @export
 */
grrUi.cron.newCronJobDeprecatedWizard.statusPageDirective.StatusPageDirective =
    function() {
  return {
    scope: {
      response: '=',
    },
    restrict: 'E',
    templateUrl: '/static/angular-components/cron/' +
        'new-cron-job-deprecated-wizard/status-page.html'
  };
};


/**
 * Directive's name in Angular.
 *
 * @const
 * @export
 */
grrUi.cron.newCronJobDeprecatedWizard.statusPageDirective.StatusPageDirective
    .directive_name = 'grrNewCronJobDeprecatedStatusPage';

});  // goog.scope
