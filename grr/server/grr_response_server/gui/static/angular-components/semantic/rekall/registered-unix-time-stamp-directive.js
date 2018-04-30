'use strict';

goog.module('grrUi.semantic.rekall.registeredUnixTimeStampDirective');
goog.module.declareLegacyNamespace();



/**
 * Directive that displays rekall UnixTimeStamp.
 *
 * @return {!angular.Directive} Directive definition object.
 * @constructor
 * @ngInject
 * @export
 */
exports.RegisteredUnixTimeStampDirective = function() {
  return {
    scope: {
      value: '='
    },
    restrict: 'E',
    templateUrl: '/static/angular-components/semantic/rekall/' +
                 'registered-unix-time-stamp.html',
  };
};


/**
 * Name of the directive in Angular.
 *
 * @const
 * @export
 */
exports.RegisteredUnixTimeStampDirective.directive_name =
    'grrRekallRegisteredUnixTimeStamp';

/**
 * Rekall MRO type corresponding to the directive.
 *
 * @const
 * @export
 */
exports.RegisteredUnixTimeStampDirective.rekall_type = 'UnixTimeStamp';
