'use strict';

goog.provide('grrUi.semantic.durationDirective.DurationController');
goog.provide('grrUi.semantic.durationDirective.DurationDirective');
goog.provide('grrUi.semantic.durationDirective.stringifySeconds');

goog.scope(function() {


/**
 * Returns true if given number has a non-zero fractional part.
 *
 * @param {number} value Value to be checked.
 * @return {boolean} True if value has a non-zero fractional part.
 * @private
 */
var hasFraction_ = function(value) {
  return (value - Math.floor(value)) > 1e-16;
};


/**
 * Returns string representation of a given duration value in seconds.
 *
 * @param {number} value Value in seconds to be stringified.
 * @return {string} Stringified value.
 */
grrUi.semantic.durationDirective.stringifySeconds = function(value) {
  if (value == 0) {
    return '0';
  }

  var newDuration = moment.duration(value, 's');

  var unit;
  var units = ['d', 'h', 'm', 's'];
  for (var i = 0; i < units.length; ++i) {
    if (!hasFraction_(newDuration.as(units[i]))) {
      unit = units[i];
      break;
    }
  }
  if (angular.isUndefined(unit)) {
    throw new Error('Internal logic error: unit can\'t be undefined.');
  }

  var n = newDuration.as(unit);
  if (unit == 'd' && n % 7 == 0) {
    n = n / 7;
    unit = 'w';
  }

  return n.toString() + unit;
};


/**
 * Controller for DurationDirective.
 *
 * @param {!angular.Scope} $scope
 * @constructor
 * @ngInject
 */
grrUi.semantic.durationDirective.DurationController = function($scope) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @type {string} */
  this.stringifiedDuration;

  this.scope_.$watch('::value', this.onValueChange.bind(this));
};

var DurationController =
    grrUi.semantic.durationDirective.DurationController;


/**
 * Handles changes of scope.value attribute.
 *
 * @param {number} newValue Timestamp value in microseconds.
 * @suppress {missingProperties} as value can be anything.
 */
DurationController.prototype.onValueChange = function(newValue) {
  var duration = newValue.value;
  if (angular.isNumber(duration)) {
    this.stringifiedDuration =
        grrUi.semantic.durationDirective.stringifySeconds(duration);
  } else {
    this.stringifiedDuration = '-';
  }
};



/**
 * Directive that displays Duration values.
 *
 * @constructor
 * @ngInject
 * @export
 */
grrUi.semantic.durationDirective.DurationDirective = function() {
  return {
    scope: {
      value: '='
    },
    restrict: 'E',
    template: '<nobr ng-if="::controller.stringifiedDuration !== undefined">' +
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
grrUi.semantic.durationDirective.DurationDirective.directive_name =
    'grrDuration';

/**
 * Semantic type corresponding to this directive.
 *
 * @const
 * @export
 */
grrUi.semantic.durationDirective.DurationDirective.semantic_type =
    'Duration';


});  // goog.scope
