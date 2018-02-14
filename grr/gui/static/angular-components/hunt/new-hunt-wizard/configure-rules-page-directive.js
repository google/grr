'use strict';

goog.module('grrUi.hunt.newHuntWizard.configureRulesPageDirective');
goog.module.declareLegacyNamespace();



/**
 * Directive for showing wizard-like forms with multiple named steps/pages.
 *
 * @return {!angular.Directive} Directive definition object.
 * @ngInject
 * @export
 */
exports.ConfigureRulesPageDirective = function() {
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
exports.ConfigureRulesPageDirective.directive_name = 'grrConfigureRulesPage';
