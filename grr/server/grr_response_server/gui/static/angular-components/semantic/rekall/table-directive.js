'use strict';

goog.module('grrUi.semantic.rekall.tableDirective');
goog.module.declareLegacyNamespace();



/**
 * Directive that displays rekall table and row messages.
 *
 * @return {!angular.Directive} Directive definition object.
 * @ngInject
 * @export
 */
exports.TableDirective = function() {
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
exports.TableDirective.directive_name = 'grrRekallTable';
