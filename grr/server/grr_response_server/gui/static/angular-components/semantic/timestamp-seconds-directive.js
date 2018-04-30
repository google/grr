'use strict';

goog.module('grrUi.semantic.timestampSecondsDirective');
goog.module.declareLegacyNamespace();



/**
 * Controller for TimestampSecondsDirective.
 *
 * @param {!angular.Scope} $scope
 * @constructor
 * @ngInject
 */
const TimestampSecondsController = function(
    $scope) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @type {?} */
  this.scope_.value;

  /** @private {number} */
  this.timestampValue;

  this.scope_.$watch('::value', this.onValueChange.bind(this));
};



/**
 * Handles changes of scope.value attribute.
 *
 * @param {number} newValue Timestamp value in seconds.
 * @suppress {missingProperties} as value can be anything.
 */
TimestampSecondsController.prototype.onValueChange = function(newValue) {
  if (angular.isDefined(newValue)) {
    var timestamp;
    if (angular.isObject(newValue)) {
      timestamp = newValue.value;
    } else {
      timestamp = newValue;
    }

    this.timestampValue = timestamp * 1000000;
  }
};


/**
 * Directive that displays RDFDatetime values.
 *
 * @return {!angular.Directive} Directive definition object.
 * @ngInject
 * @export
 */
exports.TimestampSecondsDirective = function() {
  return {
    scope: {
      value: '='
    },
    restrict: 'E',
    template: '<grr-timestamp value="::controller.timestampValue"></grr-timestamp>',
    controller: TimestampSecondsController,
    controllerAs: 'controller'
  };
};


/**
 * Directive's name in Angular.
 *
 * @const
 * @export
 */
exports.TimestampSecondsDirective.directive_name = 'grrTimestampSeconds';

/**
 * Semantic type corresponding to this directive.
 *
 * @const
 * @export
 */
exports.TimestampSecondsDirective.semantic_type = 'RDFDatetimeSeconds';
