'use strict';

goog.module('grrUi.core.troggleDirective');
goog.module.declareLegacyNamespace();

/**
 * @enum {string}
 */
const TroggleState = {
  SET: 'SET',
  UNSET: 'UNSET',
  VOID: 'VOID',
};

/**
 * @param {!TroggleState} state
 * @return {!TroggleState}
 */
const nextTroggleState = (state) => {
  switch (state) {
    case TroggleState.SET:
      return TroggleState.UNSET;
    case TroggleState.UNSET:
      return TroggleState.VOID;
    case TroggleState.VOID:
      return TroggleState.SET;
  }
  throw new Error(`invalid state: ${state}`);
};


/**
 * A toggle for trinary logic.
 *
 * Troggle is like a toggle button but can be in one of the three states
 * (contrary to two in normal toggles): set, unset or void. The exact semantics
 * of the three states are not specified and can vary depending on the context.
 *
 * By repeatedly clicking the troggle user is able to switch between the states.
 *
 * @return {!angular.Directive}
 */
const TroggleDirective = function() {
  return {
    restrict: 'E',
    templateUrl: '/static/angular-components/core/troggle.html',
    require: 'ngModel',
    link: function(scope, element, attrs, ngModelController) {
      ngModelController.$render = function() {
        scope.state = ngModelController.$viewValue;
      };

      scope.$watch('state', function() {
        ngModelController.$setViewValue(scope.state);
      });

      scope.switchState = function() {
        scope.state = nextTroggleState(scope.state);
      };
    },
  };
};

TroggleDirective.directive_name = 'grrTroggle';

exports.TroggleState = TroggleState;
exports.TroggleDirective = TroggleDirective;
