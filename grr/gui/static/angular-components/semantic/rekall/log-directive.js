'use strict';

goog.module('grrUi.semantic.rekall.logDirective');
goog.module.declareLegacyNamespace();



/**
 * Directive that displays rekall log messages.
 *
 * @return {!angular.Directive} Directive definition object.
 * @ngInject
 * @export
 */
exports.LogDirective = function() {
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
exports.LogDirective.directive_name = 'grrRekallLog';
