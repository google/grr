'use strict';

goog.module('grrUi.semantic.rekall.rekallDefaultValueDirective');
goog.module.declareLegacyNamespace();



/**
 * Directive that displays JS objects containing Rekall objects as tables.
 *
 * @return {!angular.Directive} Directive definition object.
 * @ngInject
 * @export
 */
exports.RekallDefaultValueDirective = function() {
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
exports.RekallDefaultValueDirective.directive_name = 'grrRekallDefaultValue';
