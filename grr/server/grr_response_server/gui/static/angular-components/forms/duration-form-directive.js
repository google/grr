'use strict';

goog.module('grrUi.forms.durationFormDirective');
goog.module.declareLegacyNamespace();

const {stringifySeconds} = goog.require('grrUi.semantic.durationDirective');



/**
 * Controller for DurationFormDirective.
 *
 * @constructor
 * @param {!angular.Scope} $scope
 * @ngInject
 */
const DurationFormController = function(
    $scope) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @export {string} */
  this.valueString = '';

  /** @export {boolean} */
  this.isInvalid = false;

  /** @private @const {RegExp} */
  this.regex_ = /^(\d+)([smhdw])?$/;

  this.scope_.$watch('value.value',
                     this.onValueChange_.bind(this));
  this.scope_.$watch('controller.valueString',
                     this.onValueStringChange_.bind(this));
};


/**
 * Parses given string representation of a duration value.
 *
 * @param {string} stringValue String to be parsed.
 * @return {?moment.Duration} Parsed duration object or null if parsing
 *     failed.
 * @private
 */
DurationFormController.prototype.parseString_ = function(stringValue) {
  var match = stringValue.trim().match(this.regex_);
  if (match == null) {
    return null;
  } else {
    var n = parseInt(match[1], 10);
    var unit = match[2] || 's';

    return moment.duration(n, unit);
  }
};

/**
 * Handles changes in the value bound to be edited by this directive.
 * As the value may be changed in onValueStringChange handler (i.e. when
 * user types a symbol), we're only changing this.valueString if
 * the duration it represents is different from newValue.
 *
 * @param {number} newValue New time value.
 * @private
 */
DurationFormController.prototype.onValueChange_ = function(newValue) {
  if (angular.isNumber(newValue)) {
    var currentParsedDuration = this.parseString_(this.valueString);
    // There's no need to update string representation as it's already
    // up-to-date. This check helps to avoid weird UI behavior when user
    // input is ambiguous. I.e. 24h is the same as 1d, and without this check
    // "24h" entered by the user will get converted to "1d".
    if (currentParsedDuration != null &&
        newValue == currentParsedDuration.asSeconds()) {
      return;
    }

    this.valueString = stringifySeconds(newValue);
  }
};

/**
 * Handles changes in string representation of the duration value being edited.
 * Called when user types or deletes a symbol. Updates the actual value
 * that's bound to this directive via "value" binding. Sets an "invalid"
 * flag and the value to null if the string can't be parsed for some reason.
 *
 * @param {string} newValue New string from the text input.
 * @private
 */
DurationFormController.prototype.onValueStringChange_ = function(newValue) {
  if (newValue == '') {
    this.scope_.value.value = null;
    this.isInvalid = false;
  } else {
    var duration = this.parseString_(newValue);
    this.scope_.value.value = duration !== null ? duration.asSeconds() : null;
    this.isInvalid = duration === null;
  }
};

/**
 * DurationFormDirective renders RDFDuration values..
 *
 * @return {!angular.Directive} Directive definition object.
 */
exports.DurationFormDirective = function() {
  return {
    restrict: 'E',
    scope: {
      value: '=',
      metadata: '='
    },
    templateUrl: '/static/angular-components/forms/duration-form.html',
    controller: DurationFormController,
    controllerAs: 'controller'
  };
};


/**
 * Name of the directive in Angular.
 *
 * @const
 * @export
 */
exports.DurationFormDirective.directive_name = 'grrFormDuration';

/**
 * Semantic type corresponding to this directive.
 *
 * @const
 * @export
 */
exports.DurationFormDirective.semantic_type = 'Duration';
