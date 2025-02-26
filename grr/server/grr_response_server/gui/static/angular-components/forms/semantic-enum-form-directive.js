goog.module('grrUi.forms.semanticEnumFormDirective');



/**
 * Controller for SemanticEnumFormDirective.
 * @unrestricted
 */
const SemanticEnumFormController = class {
  /**
   * @param {!angular.Scope} $scope
   * @ngInject
   */
  constructor($scope) {
    /** @private {!angular.Scope} */
    this.scope_ = $scope;

    /** @type {!Array<Object>} */
    this.allowedOptions = [];

    this.scope_.$watch(
        'metadata.allowed_values', this.onAllowedValuesChange_.bind(this));
  }

  /**
   * Handles changes of the list of allowed values.
   *
   * @param {!Array<Object>} newValue
   * @private
   */
  onAllowedValuesChange_(newValue) {
    this.allowedOptions = [];

    if (angular.isDefined(newValue)) {
      this.allowedOptions = [];
      angular.forEach(newValue, function(option) {
        let defaultLabel = '';
        const defaultOptionName = this.scope_.$eval('metadata.default.value');
        if (defaultOptionName == option.name) {
          defaultLabel = ' (default)';
        }

        let label = option.name;
        if (option.doc) {
          label = option.doc;
        }

        this.allowedOptions.push(
            {value: option.name, label: label + defaultLabel});
      }.bind(this));
    }
  }
};



/**
 * SemanticEnumFormDirective renders an EnumNamedValue.
 *
 * @return {!angular.Directive} Directive definition object.
 */
exports.SemanticEnumFormDirective = function() {
  return {
    restrict: 'E',
    scope: {value: '=', metadata: '='},
    templateUrl: '/static/angular-components/forms/semantic-enum-form.html',
    controller: SemanticEnumFormController,
    controllerAs: 'controller'
  };
};


/**
 * Name of the directive in Angular.
 *
 * @const
 * @export
 */
exports.SemanticEnumFormDirective.directive_name = 'grrFormEnum';

/**
 * Semantic type corresponding to this directive.
 *
 * @const
 * @export
 */
exports.SemanticEnumFormDirective.semantic_type = 'EnumNamedValue';
