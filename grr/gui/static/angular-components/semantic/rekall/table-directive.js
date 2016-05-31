'use strict';

goog.provide('grrUi.semantic.rekall.tableDirective.TableDirective');

goog.scope(function() {

/**
 * Directive that displays rekall table and row messages.
 *
 * @return {!angular.Directive} Directive definition object.
 * @constructor
 * @ngInject
 * @export
 */
grrUi.semantic.rekall.tableDirective.TableDirective = function() {
  return {
    scope: {
      value: '='
    },
    restrict: 'E',
    templateUrl: '/static/angular-components/semantic/rekall/table.html',
  };
};


/**
 * Name of the directive in Angular.
 *
 * @const
 * @export
 */
grrUi.semantic.rekall.tableDirective.TableDirective.directive_name =
    'grrRekallTable';

});  // goog.scope
