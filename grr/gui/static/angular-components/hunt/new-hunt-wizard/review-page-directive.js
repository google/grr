'use strict';

goog.provide('grrUi.hunt.newHuntWizard.reviewPageDirective.ReviewPageDirective');

goog.scope(function() {

/**
 * Directive for showing wizard-like forms with multiple named steps/pages.
 *
 * @return {!angular.Directive} Directive definition object.
 * @ngInject
 * @export
 */
grrUi.hunt.newHuntWizard.reviewPageDirective.ReviewPageDirective = function() {
  return {
    scope: {
      createHuntArgs: '='
    },
    restrict: 'E',
    templateUrl: '/static/angular-components/hunt/new-hunt-wizard/' +
        'review-page.html'
  };
};


/**
 * Directive's name in Angular.
 *
 * @const
 * @export
 */
grrUi.hunt.newHuntWizard.reviewPageDirective
    .ReviewPageDirective
    .directive_name = 'grrNewHuntReviewPage';
});  // goog.scope
