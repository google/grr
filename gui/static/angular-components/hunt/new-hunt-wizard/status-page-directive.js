'use strict';

goog.provide('grrUi.hunt.newHuntWizard.statusPageDirective.StatusPageDirective');

goog.scope(function() {

/**
 * Directive for showing wizard-like forms with multiple named steps/pages.
 *
 * @constructor
 * @ngInject
 * @export
 */
grrUi.hunt.newHuntWizard.statusPageDirective.StatusPageDirective = function() {
  return {
    scope: {
      response: '=',
    },
    restrict: 'E',
    templateUrl: '/static/angular-components/hunt/new-hunt-wizard/' +
        'status-page.html'
  };
};


/**
 * Directive's name in Angular.
 *
 * @const
 * @export
 */
grrUi.hunt.newHuntWizard.statusPageDirective.StatusPageDirective
    .directive_name = 'grrNewHuntStatusPage';

});  // goog.scope
