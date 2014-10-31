'use strict';

goog.provide('grrUi.hunt.huntErrorsDirective.HuntErrorsDirective');

goog.scope(function() {



/**
 * Directive for displaying errors of a hunt with a given URN.
 *
 * @constructor
 * @ngInject
 * @export
 */
grrUi.hunt.huntErrorsDirective.HuntErrorsDirective = function() {
  return {
    scope: {
      huntUrn: '@'
    },
    restrict: 'E',
    templateUrl: 'static/angular-components/hunt/hunt-errors.html',
    link: function(scope, element) {
      scope.$watch('huntUrn', function() {
        scope.errorsUrn = scope.huntUrn + '/ErrorClients';
      });
    }
  };
};


/**
 * Directive's name in Angular.
 */
grrUi.hunt.huntErrorsDirective.HuntErrorsDirective.directive_name =
    'grrHuntErrors';

});  // goog.scope
