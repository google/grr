'use strict';

goog.provide('grrUi.forms.semanticPrimitiveFormDirective');
goog.provide('grrUi.forms.semanticPrimitiveFormDirective.SemanticPrimitiveFormDirective');


/**
 * Controller for SemanticPrimitiveFormDirective.
 *
 * @constructor
 * @param {!angular.Scope} $scope
 * @param {!grrUi.core.reflectionService.ReflectionService} grrReflectionService
 * @ngInject
 */
const SemanticPrimitiveFormController =
    function($scope, grrReflectionService) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @private {!grrUi.core.reflectionService.ReflectionService} */
  this.grrReflectionService_ = grrReflectionService;

  /** @export {string|undefined} */
  this.valueType;

  this.scope_.$watch('value.type', this.onValueTypeChange_.bind(this));
};


/**
 * Handles changes of the value type.
 *
 * @param {string|undefined} newValue
 * @private
 */
SemanticPrimitiveFormController.prototype.onValueTypeChange_ = function(
    newValue) {
  // We use direct equality instead of `angular.isUndefined` because otherwise
  // Closure Compiler is not able to infer that `newValue` passed to a method
  // below is not `undefined`.
  if (newValue === undefined) {
    this.valueType = undefined;
    return;
  }

  var descriptorHandler = function(descriptor) {
    var allowedTypes = grrUi.forms.semanticPrimitiveFormDirective
        .SemanticPrimitiveFormDirective.semantic_types;
    var typeIndex = -1;
    angular.forEach(
        allowedTypes, function(type) {
          var index = descriptor['mro'].indexOf(type);
          if (index != -1 && (typeIndex == -1 || typeIndex > index)) {
            typeIndex = index;
            this.valueType = type;
          }
        }.bind(this));

    if (!this.valueType) {
      this.valueType = 'RDFString';
    }
  }.bind(this);

  this.grrReflectionService_.getRDFValueDescriptor(newValue)
      .then(descriptorHandler);
};

/**
 * SemanticPrimitiveFormDirective renders a form for a boolean value.
 *
 * @return {!angular.Directive} Directive definition object.
 */
grrUi.forms.semanticPrimitiveFormDirective.SemanticPrimitiveFormDirective =
    function() {
  return {
    restrict: 'E',
    scope: {
      value: '='
    },
    templateUrl: '/static/angular-components/forms/' +
        'semantic-primitive-form.html',
    controller: SemanticPrimitiveFormController,
    controllerAs: 'controller'
  };
};


/**
 * Name of the directive in Angular.
 *
 * @const
 * @export
 */
grrUi.forms.semanticPrimitiveFormDirective.SemanticPrimitiveFormDirective
    .directive_name = 'grrFormPrimitive';


/**
 * Semantic type corresponding to this directive.
 *
 * @const
 * @export
 */
grrUi.forms.semanticPrimitiveFormDirective.SemanticPrimitiveFormDirective
    .semantic_types = ['RDFBool', 'bool',
                       'RDFInteger', 'int', 'long', 'float',
                       'RDFString', 'basestring', 'RDFURN',
                       // TODO(user): check if we ever have to deal with
                       // bytes type (RDFBytes is handled by grr-form-bytes).
                       'bytes'];
