'use strict';

goog.provide('grrUi.hunt.newHuntWizard.configureHuntPageDirective.ConfigureHuntPageController');
goog.provide('grrUi.hunt.newHuntWizard.configureHuntPageDirective.ConfigureHuntPageDirective');

goog.scope(function() {

/**
 * Directive for configuring hunt runner parameters.

 * @return {angular.Directive} Directive definition object.
 */
grrUi.hunt.newHuntWizard.configureHuntPageDirective
    .ConfigureHuntPageDirective = function() {
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
grrUi.hunt.newHuntWizard.configureHuntPageDirective
    .ConfigureHuntPageDirective.directive_name = 'grrConfigureHuntPage';

});  // goog.scope
