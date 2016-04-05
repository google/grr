'use strict';

goog.provide('grrUi.forms.semanticEnumFormDirective');
goog.provide('grrUi.forms.semanticEnumFormDirective.SemanticEnumFormController');
goog.provide('grrUi.forms.semanticEnumFormDirective.SemanticEnumFormDirective');


/**
 * Controller for SemanticEnumFormDirective.
 *
 * @constructor
 * @param {!angular.Scope} $scope
 * @ngInject
 */
grrUi.forms.semanticEnumFormDirective.SemanticEnumFormController = function(
    $scope) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @type {!Array<Object>} */
  this.allowedOptions = [];

  this.scope_.$watch('metadata.allowed_values',
                     this.onAllowedValuesChange_.bind(this));
};
var SemanticEnumFormController =
    grrUi.forms.semanticEnumFormDirective.SemanticEnumFormController;


/**
 * Handles changes of the list of allowed values.
 *
 * @param {!Array<Object>} newValue
 * @private
 */
SemanticEnumFormController.prototype.onAllowedValuesChange_ = function(
    newValue) {
  this.allowedOptions = [];

  if (angular.isDefined(newValue)) {
    this.allowedOptions = [];
    angular.forEach(newValue, function(option) {
      var defaultLabel = '';
      var defaultOptionName = this.scope_.$eval('metadata.default.value');
      if (defaultOptionName == option.name) {
        defaultLabel = ' (default)';
      }

      var label = option.name;
      if (option.doc) {
        label = option.doc;
      }

      this.allowedOptions.push({
        value: option.name,
        label: label + defaultLabel
      });
    }.bind(this));
  }
};

/**
 * SemanticEnumFormDirective renders an EnumNamedValue.
 *
 * @return {!angular.Directive} Directive definition object.
 */
grrUi.forms.semanticEnumFormDirective.SemanticEnumFormDirective = function() {
  return {
    restrict: 'E',
    scope: {
      value: '=',
      metadata: '='
    },
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
grrUi.forms.semanticEnumFormDirective.SemanticEnumFormDirective
    .directive_name = 'grrFormEnum';

/**
 * Semantic type corresponding to this directive.
 *
 * @const
 * @export
 */
grrUi.forms.semanticEnumFormDirective.SemanticEnumFormDirective
    .semantic_type = 'EnumNamedValue';
