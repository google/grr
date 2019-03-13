goog.module('grrUi.forms.datetimeFormDirective');
goog.module.declareLegacyNamespace();

/**
 * Controller for DatetimeFormDirective.
 */
class DatetimeFormController {
  /**
   * @param {!angular.Scope} $scope
   * @ngInject
   */
  constructor($scope) {
    /** @private @const {!angular.Scope} */
    this.scope_ = $scope;

    /** @export {string} */
    this.valueString = '';

    /** @export {boolean} */
    this.isInvalid = false;

    /** @export {string} */
    this.format = 'YYYY-MM-DD HH:mm';

    /** @export {string} */
    this.example = moment.utc().format(this.format);

    this.scope_.$watch('value.value', (val) => this.onValueChange_(val));
    this.scope_.$watch(
        'controller.valueString', (val) => this.onValueStringChange_(val));
  }

  /**
   * Handles changes in the value bound to be edited by this directive.
   * As the value may be changed in onValueStringChange handler (i.e. when
   * user types a symbol), we're only changing this.valueString if
   * the moment it represents is different from newValue.
   *
   * @param {number} newValue New time value.
   * @private
   */
  onValueChange_(newValue) {
    if (newValue === undefined || newValue === null) {
      // Do not update the input field value, if:
      // - it is unset, to avoid infinite recursion.
      // - it is invalid, to avoid clearing the text field while the user types.
      if (this.valueString && !this.isInvalid) {
        this.valueString = '';
      }
      return;
    }

    const parsed = moment.utc(newValue / 1000);
    if (!parsed.isValid()) {
      this.valueString = '';
      return;
    }

    // Do not update the input field value, if it matches the formatted value,
    // e.g. when only the seconds are updated, which are not displayed.
    if (this.valueString === parsed.format(this.format)) {
      return;
    }

    this.valueString = parsed.format(this.format);
  }

  /**
   * Handles changes in string representation of the time value being edited.
   * Called when user types or deletes a symbol. Updates the actual value
   * that's bound to this directive via "value" binding. Sets an "invalid"
   * flag and the value to null if the string can't be parsed for some reason.
   *
   * @param {string} newValue New string from the text input.
   * @private
   */
  onValueStringChange_(newValue) {
    const parsed = moment.utc(newValue, this.format, true);
    this.isInvalid = !parsed.isValid();

    if (parsed.isValid()) {
      this.scope_.value.value = parsed.valueOf() * 1000;
    } else {
      this.scope_.value.value = null;
    }
  }

  /**
   * Sets value to the current time.
   *
   * @export
   */
  today() {
    this.scope_.value.value = moment().valueOf() * 1000;
  }
}

/**
 * DatetimeFormDirective renders RDFDatetime values..
 *
 * @return {!angular.Directive} Directive definition object.
 */
exports.DatetimeFormDirective = function() {
  return {
    restrict: 'E',
    scope: {value: '=', metadata: '='},
    templateUrl: '/static/angular-components/forms/datetime-form.html',
    controller: DatetimeFormController,
    controllerAs: 'controller'
  };
};


/**
 * Name of the directive in Angular.
 *
 * @const
 * @export
 */
exports.DatetimeFormDirective.directive_name = 'grrFormDatetime';

/**
 * Semantic type corresponding to this directive.
 *
 * @const
 * @export
 */
exports.DatetimeFormDirective.semantic_type = 'RDFDatetime';
