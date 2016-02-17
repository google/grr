'use strict';

goog.provide('grrUi.hunt.newHuntWizard.configureRulesPageDirective.ConfigureRulesPageDirective');

goog.scope(function() {

/**
 * Directive for showing wizard-like forms with multiple named steps/pages.
 *
 * @constructor
 * @ngInject
 * @export
 */
grrUi.hunt.newHuntWizard.configureRulesPageDirective
    .ConfigureRulesPageDirective = function() {
  return {
    scope: {
      clientRuleSet: '=',
    },
    restrict: 'E',
    templateUrl: '/static/angular-components/hunt/new-hunt-wizard/' +
        'configure-rules-page.html',
  };
};


/**
 * Directive's name in Angular.
 *
 * @const
 * @export
 */
grrUi.hunt.newHuntWizard.configureRulesPageDirective
    .ConfigureRulesPageDirective
    .directive_name = 'grrConfigureRulesPage';

});  // goog.scope
