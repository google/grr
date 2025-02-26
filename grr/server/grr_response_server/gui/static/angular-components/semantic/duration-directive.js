goog.module('grrUi.semantic.durationDirective');
goog.module.declareLegacyNamespace();



/**
 * Returns true if given number has a non-zero fractional part.
 *
 * @param {number} value Value to be checked.
 * @return {boolean} True if value has a non-zero fractional part.
 * @private
 */
const hasFraction_ = function(value) {
  return (value - Math.floor(value)) > 1e-16;
};


/**
 * Returns string representation of a given duration value in seconds.
 *
 * @param {number} value Value in seconds to be stringified.
 * @return {string} Stringified value.
 */
exports.stringifySeconds = function(value) {
  if (value == 0) {
    return '0';
  }

  const newDuration = moment.duration(value, 's');

  let unit;
  const units = ['d', 'h', 'm', 's'];
  for (let i = 0; i < units.length; ++i) {
    if (!hasFraction_(newDuration.as(units[i]))) {
      unit = units[i];
      break;
    }
  }
  if (angular.isUndefined(unit)) {
    throw new Error('Internal logic error: unit can\'t be undefined.');
  }

  let n = newDuration.as(unit);
  if (unit == 'd' && n % 7 == 0) {
    n = n / 7;
    unit = 'w';
  }

  return n.toString() + unit;
};


/**
 * Controller for DurationDirective.
 * @unrestricted
 */
const DurationController = class {
  /**
   * @param {!angular.Scope} $scope
   * @ngInject
   */
  constructor($scope) {
    /** @private {!angular.Scope} */
    this.scope_ = $scope;

    /** @type {string} */
    this.stringifiedDuration;

    this.scope_.$watch('::value', this.onValueChange.bind(this));
  }

  /**
   * Handles changes of scope.value attribute.
   *
   * @param {{value: number}} newValue A wrapped duration object carrying number
   *     of microseconds.
   */
  onValueChange(newValue) {
    if (newValue !== undefined && angular.isNumber(newValue.value)) {
      const duration = newValue.value;
      this.stringifiedDuration = exports.stringifySeconds(duration);
    } else {
      this.stringifiedDuration = '-';
    }
  }
};



/**
 * Directive that displays DurationSeconds values.
 *
 * @return {!angular.Directive} Directive definition object.
 * @ngInject
 * @export
 */
exports.DurationDirective = function() {
  return {
    scope: {value: '='},
    restrict: 'E',
    template: '<nobr ng-if="::controller.stringifiedDuration">' +
        '{$ ::controller.stringifiedDuration $}</nobr>',
    controller: DurationController,
    controllerAs: 'controller'
  };
};


/**
 * Name of the directive in Angular.
 *
 * @const
 * @export
 */
exports.DurationDirective.directive_name = 'grrDuration';

/**
 * Semantic type corresponding to this directive.
 *
 * @const
 * @export
 */
exports.DurationDirective.semantic_type = 'DurationSeconds';
