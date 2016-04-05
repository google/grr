'use strict';

goog.provide('grrUi.cron.newCronJobWizard.reviewPageDirective.ReviewPageDirective');

goog.scope(function() {

/**
 * Directive for showing wizard-like forms with multiple named steps/pages.
 *
 * @constructor
 * @ngInject
 * @export
 */
grrUi.cron.newCronJobWizard.reviewPageDirective
    .ReviewPageDirective = function() {
  return {
    scope: {
      cronJob: '='
    },
    restrict: 'E',
    templateUrl: '/static/angular-components/cron/new-cron-job-wizard/' +
        'review-page.html',
    controllerAs: 'controller'
  };
};


/**
 * Directive's name in Angular.
 *
 * @const
 * @export
 */
grrUi.cron.newCronJobWizard.reviewPageDirective
    .ReviewPageDirective
    .directive_name = 'grrNewCronJobReviewPage';

});  // goog.scope
