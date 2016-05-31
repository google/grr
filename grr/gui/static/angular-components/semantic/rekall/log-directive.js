'use strict';

goog.provide('grrUi.semantic.rekall.logDirective.LogDirective');

goog.scope(function() {

/**
 * Directive that displays rekall log messages.
 *
 * @return {!angular.Directive} Directive definition object.
 * @constructor
 * @ngInject
 * @export
 */
grrUi.semantic.rekall.logDirective.LogDirective = function() {
  return {
    scope: {
      value: '='
    },
    restrict: 'E',
    templateUrl: '/static/angular-components/semantic/rekall/log.html',
  };
};


/**
 * Name of the directive in Angular.
 *
 * @const
 * @export
 */
grrUi.semantic.rekall.logDirective.LogDirective.directive_name =
    'grrRekallLog';

});  // goog.scope
