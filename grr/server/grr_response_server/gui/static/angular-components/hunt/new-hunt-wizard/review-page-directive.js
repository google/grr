'use strict';

goog.module('grrUi.hunt.newHuntWizard.reviewPageDirective');
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
exports.ReviewPageDirective.directive_name = 'grrNewHuntReviewPage';
