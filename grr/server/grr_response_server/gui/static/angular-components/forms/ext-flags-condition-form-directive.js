goog.module('grrUi.forms.extFlagsConditionFormDirective');


/**
 * A controller for the `FileFinderExtFlagsCondition`.
 * @unrestricted
 */
const ExtFlagsConditionFormController = class {
  /**
   * @param {!angular.Scope} $scope
   * @ngInject
   */
  constructor($scope) {
    this.linuxPickerShown = false;
    this.osxPickerShown = false;
  }
};

/**
 * A directive for the `FileFinderExtFlagsCondition`.
 *
 * @return {!angular.Directive} Directive definition object.
 */
const ExtFlagsConditionFormDirective = function() {
  return {
    restrict: 'E',
    scope: {
      value: '=',
    },
    templateUrl:
        '/static/angular-components/forms/ext-flags-condition-form.html',
    controller: ExtFlagsConditionFormController,
    controllerAs: 'controller',
  };
};

/**
 * Name of the directive in Angular.
 *
 * @const
 * @export
 */
ExtFlagsConditionFormDirective.directive_name = 'grrExtFlagsConditionForm';

/**
 * Semantic type corresponding to this directive.
 *
 * @const
 * @export
 */
ExtFlagsConditionFormDirective.semantic_type = 'FileFinderExtFlagsCondition';

exports.ExtFlagsConditionFormDirective = ExtFlagsConditionFormDirective;
