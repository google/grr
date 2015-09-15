'use strict';

goog.provide('grrUi.hunt.huntsViewDirective.HuntsViewDirective');

goog.scope(function() {


/**
 * HuntsViewDirective definition.
 * @return {angular.Directive} Directive definition object.
 */
grrUi.hunt.huntsViewDirective.HuntsViewDirective = function() {
  return {
    restrict: 'E',
    scope: {},
    templateUrl: '/static/angular-components/hunt/hunts-view.html',
    link: function(scope) {
      scope.selection = {};
    }
  };
};


/**
 * Name of the directive in Angular.
 *
 * @const
 * @export
 */
grrUi.hunt.huntsViewDirective.HuntsViewDirective.directive_name =
    'grrHuntsView';

});  // goog.scope
