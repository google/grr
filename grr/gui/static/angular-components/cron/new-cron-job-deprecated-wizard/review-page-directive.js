'use strict';

goog.provide('grrUi.cron.newCronJobDeprecatedWizard.reviewPageDirective.ReviewPageDirective');

goog.scope(function() {

/**
 * Directive for showing wizard-like forms with multiple named steps/pages.
 *
 * @constructor
 * @ngInject
 * @export
 */
grrUi.cron.newCronJobDeprecatedWizard.reviewPageDirective
    .ReviewPageDirective = function() {
  return {
    scope: {
      cronJob: '='
    },
    restrict: 'E',
    templateUrl: '/static/angular-components/cron/' +
        'new-cron-job-deprecated-wizard/review-page.html',
    controllerAs: 'controller'
  };
};


/**
 * Directive's name in Angular.
 *
 * @const
 * @export
 */
grrUi.cron.newCronJobDeprecatedWizard.reviewPageDirective
    .ReviewPageDirective
    .directive_name = 'grrNewCronJobDeprecatedReviewPage';

});  // goog.scope
