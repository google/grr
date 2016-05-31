'use strict';

goog.provide('grrUi.semantic.rekall.rekallDefaultValueDirective.RekallDefaultValueDirective');

goog.scope(function() {

/**
 * Directive that displays JS objects containing Rekall objects as tables.
 *
 * @return {!angular.Directive} Directive definition object.
 * @constructor
 * @ngInject
 * @export
 */
grrUi.semantic.rekall.rekallDefaultValueDirective.RekallDefaultValueDirective =
    function() {
  return {
    scope: {
      value: '='
    },
    restrict: 'E',
    templateUrl:
        '/static/angular-components/semantic/rekall/rekall-default-value.html',
  };
};


/**
 * Name of the directive in Angular.
 *
 * @const
 * @export
 */
grrUi.semantic.rekall.rekallDefaultValueDirective.RekallDefaultValueDirective.
    directive_name = 'grrRekallDefaultValue';

});  // goog.scope
