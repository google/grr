'use strict';

goog.module('grrUi.cron.newCronJobWizard.reviewPageDirective');
goog.module.declareLegacyNamespace();



/**
 * Directive for showing wizard-like forms with multiple named steps/pages.
 *
 * @return {!angular.Directive} Directive definition object.
 * @ngInject
 * @export
 */
exports.ReviewPageDirective = function() {
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
exports.ReviewPageDirective.directive_name = 'grrNewCronJobReviewPage';
