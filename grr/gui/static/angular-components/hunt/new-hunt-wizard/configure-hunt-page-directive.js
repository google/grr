'use strict';

goog.module('grrUi.hunt.newHuntWizard.configureHuntPageDirective');
goog.module.declareLegacyNamespace();



/**
 * Directive for configuring hunt runner parameters.

 * @return {angular.Directive} Directive definition object.
 */
exports.ConfigureHuntPageDirective = function() {
  return {
    scope: {
      huntRunnerArgs: '=',
    },
    restrict: 'E',
    templateUrl: '/static/angular-components/hunt/new-hunt-wizard/' +
        'configure-hunt-page.html'
  };
};


/**
 * Directive's name in Angular.
 *
 * @const
 * @export
 */
exports.ConfigureHuntPageDirective.directive_name = 'grrConfigureHuntPage';
