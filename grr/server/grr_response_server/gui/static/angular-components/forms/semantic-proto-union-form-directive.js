'use strict';

goog.module('grrUi.forms.semanticProtoUnionFormDirective');
goog.module.declareLegacyNamespace();


/**
 * Controller for SemanticProtoUnionFormDirective.
 *
 * @constructor
 * @param {!angular.Scope} $scope
 * @ngInject
 */
const SemanticProtoUnionFormController = function($scope) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @type {Object|undefined} */
  this.unionField;

  /** @type {string|undefined} */
  this.unionFieldValue;

  $scope.$watch('descriptor', this.onDescriptorChange_.bind(this));
  $scope.$watch('value.value[controller.unionField.name].value',
                this.onUnionFieldValueChange_.bind(this));
};


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
* @param {?string} oldValue
* @private
*/
SemanticProtoUnionFormController.prototype.onUnionFieldValueChange_ = function(
    newValue, oldValue) {
  if (angular.isDefined(newValue)) {
    if (angular.isDefined(oldValue) &&
        oldValue !== newValue) {
      var unionPart = this.scope_['value']['value'][this.unionFieldValue];

      if (angular.isObject(unionPart)) {
        // We have to make sure that we replace the object at
        // value.value[controller.unionFieldValue]
        unionPart['value'] = {};
        this.scope_['value']['value'][this.unionFieldValue] =
            angular.copy(unionPart);
      }
    }

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
exports.SemanticProtoUnionFormDirective = function() {
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
exports.SemanticProtoUnionFormDirective.directive_name = 'grrFormProtoUnion';
