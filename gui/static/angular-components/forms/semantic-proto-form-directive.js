'use strict';

goog.provide('grrUi.forms.semanticProtoFormDirective.SemanticProtoFormController');
goog.provide('grrUi.forms.semanticProtoFormDirective.SemanticProtoFormDirective');


/**
 * Controller for SemanticProtoFormDirective.
 *
 * @constructor
 * @param {!angular.Scope} $scope
 * @param {!grrUi.core.reflectionService.ReflectionService} grrReflectionService
 * @ngInject
 */
grrUi.forms.semanticProtoFormDirective.SemanticProtoFormController = function(
    $scope, grrReflectionService) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @type {?} */
  this.scope_.value;

  /** @private {!grrUi.core.reflectionService.ReflectionService} */
  this.grrReflectionService_ = grrReflectionService;

  /** @type {boolean} */
  this.advancedShown = false;

  /** @type {boolean} */
  this.hasAdvancedFields = false;

  /** @type {boolean} */
  this.expanded = false;

  this.scope_.$watch('value', this.onValueChange_.bind(this));
};
var SemanticProtoFormController =
    grrUi.forms.semanticProtoFormDirective.SemanticProtoFormController;


/**
 * Predicate that returns true only for regular (non-hidden, non-advanced)
 * fields.
 *
 * @param {Object} field Descriptor field to check.
 * @param {Number} index Descriptor field index.
 * @return {boolean}
 * @export
 */
SemanticProtoFormController.prototype.regularFieldsOnly = function(
    field, index) {
  return angular.isUndefined(field.labels) ||
      field.labels.indexOf('HIDDEN') == -1 &&
      field.labels.indexOf('ADVANCED') == -1;
};


/**
 * Predicate that returns true only for advanced (and non-hidden) fields.
 *
 * @param {Object} field Descriptor field to check.
 * @param {Number} index Descriptor field index.
 * @return {boolean}
 * @export
 */
SemanticProtoFormController.prototype.advancedFieldsOnly = function(
    field, index) {
  return angular.isDefined(field.labels) &&
      field.labels.indexOf('HIDDEN') == -1 &&
      field.labels.indexOf('ADVANCED') != -1;
};


/**
 * Handles changes of the value type.
 *
 * @param {?string} newValue
 * @param {?string} oldValue
 * @private
 */
SemanticProtoFormController.prototype.onValueChange_ = function(
    newValue, oldValue) {
  if (angular.isUndefined(newValue)) {
    this.descriptors = undefined;
    this.valueDescriptor = undefined;
    return;
  }

  if (newValue !== oldValue || angular.isUndefined(this.valueDescriptor)) {
    this.grrReflectionService_.getRDFValueDescriptor(
        this.scope_.value.type, true).then(
            this.onDescriptorsFetched_.bind(this));
  }
};


/**
 * Handles fetched reflection data.
 *
 * @param {!Object<string, Object>} descriptors
 * @private
 */
SemanticProtoFormController.prototype.onDescriptorsFetched_ = function(
    descriptors) {
  this.descriptors = descriptors;
  this.valueDescriptor = angular.copy(descriptors[this.scope_.value.type]);

  if (angular.isUndefined(this.scope_.value.value)) {
    this.scope_.value.value = {};
  }

  angular.forEach(this.valueDescriptor['fields'], function(field) {
    if (angular.isDefined(field.labels)) {
      if (field.labels.indexOf('HIDDEN') != -1) {
        return;
      }

      if (field.labels.indexOf('ADVANCED') != -1) {
        this.hasAdvancedFields = true;
      }
    }

    if (field.repeated) {
      field.depth = 0;

      if (angular.isUndefined(this.scope_.value.value[field.name])) {
        this.scope_.value.value[field.name] = [];
      }
    } else {
      field.depth = (this.scope_.$eval('metadata.depth') || 0) + 1;

      if (angular.isUndefined(this.scope_.value.value[field.name])) {
        if (angular.isDefined(field['default'])) {
          this.scope_.value.value[field.name] = angular.copy(field['default']);
        } else {
          this.scope_.value.value[field.name] = angular.copy(
              descriptors[field.type]['default']);
        }
      }
    }
  }.bind(this));
};

/**
 * SemanticProtoFormDirective renders a form corresponding to a given
 * RDFProtoStruct.
 *
 * @return {!angular.Directive} Directive definition object.
 */
grrUi.forms.semanticProtoFormDirective.SemanticProtoFormDirective = function() {
  return {
    scope: {
      value: '=',
      metadata: '=?'
    },
    restrict: 'E',
    templateUrl: '/static/angular-components/forms/semantic-proto-form.html',
    controller: SemanticProtoFormController,
    controllerAs: 'controller'
  };
};


/**
 * Name of the directive in Angular.
 *
 * @const
 * @export
 */
grrUi.forms.semanticProtoFormDirective.SemanticProtoFormDirective
    .directive_name = 'grrFormProto';


/**
 * Semantic type corresponding to this directive.
 *
 * @const
 * @export
 */
grrUi.forms.semanticProtoFormDirective.SemanticProtoFormDirective
    .semantic_type = 'RDFProtoStruct';
