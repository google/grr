'use strict';

goog.provide('grrUi.semantic.rekall.registeredUnixTimeStampDirective.RegisteredUnixTimeStampDirective');

goog.scope(function() {

/**
 * Directive that displays rekall UnixTimeStamp.
 *
 * @return {!angular.Directive} Directive definition object.
 * @constructor
 * @ngInject
 * @export
 */
grrUi.semantic.rekall.registeredUnixTimeStampDirective.
    RegisteredUnixTimeStampDirective = function() {
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
grrUi.semantic.rekall.registeredUnixTimeStampDirective.
    RegisteredUnixTimeStampDirective.directive_name =
        'grrRekallRegisteredUnixTimeStamp';

/**
 * Rekall MRO type corresponding to the directive.
 *
 * @const
 * @export
 */
grrUi.semantic.rekall.registeredUnixTimeStampDirective.
    RegisteredUnixTimeStampDirective.rekall_type = 'UnixTimeStamp';

});  // goog.scope
