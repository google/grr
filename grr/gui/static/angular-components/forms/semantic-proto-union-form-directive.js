'use strict';

goog.provide('grrUi.forms.semanticProtoUnionFormDirective.SemanticProtoUnionFormController');
goog.provide('grrUi.forms.semanticProtoUnionFormDirective.SemanticProtoUnionFormDirective');

/**
 * Controller for SemanticProtoUnionFormDirective.
 *
 * @constructor
 * @param {!angular.Scope} $scope
 * @ngInject
 */
grrUi.forms.semanticProtoUnionFormDirective
    .SemanticProtoUnionFormController = function($scope) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @type {Object} */
  this.unionField;

  /** @type {?string} */
  this.unionFieldValue;

  $scope.$watch('descriptor', this.onDescriptorChange_.bind(this));
  $scope.$watch('value.value[controller.unionField.name].value',
                this.onUnionFieldValueChange_.bind(this));
};
var SemanticProtoUnionFormController =
    grrUi.forms.semanticProtoUnionFormDirective
    .SemanticProtoUnionFormController;


/**
 * Handles changes of the descriptor.
 *
 * @param {Object} newValue
 * @private
 */
SemanticProtoUnionFormController.prototype.onDescriptorChange_ = function(
    newValue) {
  if (angular.isUndefined(newValue)) {
    this.unionField = undefined;
  } else {
    angular.forEach(newValue['fields'], function(field) {
      if (field.name == newValue['union_field']) {
        this.unionField = field;
      }
    }.bind(this));
  }
};


/**
 * Handles changes of the union field value.
 *
 * @param {?string} newValue
 * @private
 */
SemanticProtoUnionFormController.prototype.onUnionFieldValueChange_ = function(
    newValue) {
  if (angular.isDefined(newValue)) {
    this.unionFieldValue = newValue.toLowerCase();
  } else {
    this.unionFieldValue = undefined;
  }
};


/**
 * SemanticProtoUnionFormDirective renders a form corresponding to a
 * an RDFProtoStruct with a union field. This kind of RDFProtoStructs behave
 * similarly to C union types. They have a type defined by the union field.
 * This type determines which nested structure is used/inspected.
 *
 * @return {!angular.Directive} Directive definition object.
 */
grrUi.forms.semanticProtoUnionFormDirective
    .SemanticProtoUnionFormDirective = function() {
  return {
    scope: {
      value: '=',
      descriptor: '='
    },
    restrict: 'E',
    templateUrl: '/static/angular-components/forms/' +
        'semantic-proto-union-form.html',
    controller: SemanticProtoUnionFormController,
    controllerAs: 'controller'
  };
};


/**
 * Name of the directive in Angular.
 *
 * @const
 * @export
 */
grrUi.forms.semanticProtoUnionFormDirective
    .SemanticProtoUnionFormDirective.directive_name = 'grrFormProtoUnion';
