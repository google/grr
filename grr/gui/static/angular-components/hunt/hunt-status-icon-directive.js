'use strict';

goog.module('grrUi.hunt.huntStatusIconDirective');
goog.module.declareLegacyNamespace();



/**
 * Directive that displays hunt status icons for a given hunt.
 *
 * @return {!angular.Directive} Directive definition object.
 * @ngInject
 * @export
 */
exports.HuntStatusIconDirective = function() {
  return {
    scope: {hunt: '='},
    restrict: 'E',
    templateUrl: '/static/angular-components/hunt/hunt-status-icon.html'
  };
};


/**
 * Name of the directive in Angular.
 */
exports.HuntStatusIconDirective.directive_name = 'grrHuntStatusIcon';
