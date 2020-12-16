goog.module('grrUi.forms.semanticPrimitiveFormDirective');
goog.module.declareLegacyNamespace();

const reflectionService = goog.requireType('grrUi.core.reflectionService');



/**
 * Controller for SemanticPrimitiveFormDirective.
 * @unrestricted
 */
const SemanticPrimitiveFormController = class {
  /**
   * @param {!angular.Scope} $scope
   * @param {!reflectionService.ReflectionService}
   *     grrReflectionService
   * @ngInject
   */
  constructor($scope, grrReflectionService) {
    /** @private {!angular.Scope} */
    this.scope_ = $scope;

    /** @private {!reflectionService.ReflectionService} */
    this.grrReflectionService_ = grrReflectionService;

    /** @export {string|undefined} */
    this.valueType;

    this.scope_.$watch('value.type', this.onValueTypeChange_.bind(this));
  }

  /**
   * Handles changes of the value type.
   *
   * @param {string|undefined} newValue
   * @private
   */
  onValueTypeChange_(newValue) {
    // We use direct equality instead of `angular.isUndefined` because otherwise
    // Closure Compiler is not able to infer that `newValue` passed to a method
    // below is not `undefined`.
    if (newValue === undefined) {
      this.valueType = undefined;
      return;
    }

    var descriptorHandler = function(descriptor) {
      var allowedTypes = exports.SemanticPrimitiveFormDirective.semantic_types;
      var typeIndex = -1;
      angular.forEach(allowedTypes, function(type) {
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

    this.grrReflectionService_.getRDFValueDescriptor(newValue).then(
        descriptorHandler);
  }
};



/**
 * SemanticPrimitiveFormDirective renders a form for a boolean value.
 *
 * @return {!angular.Directive} Directive definition object.
 */
exports.SemanticPrimitiveFormDirective = function() {
  return {
    restrict: 'E',
    scope: {value: '='},
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
exports.SemanticPrimitiveFormDirective.directive_name = 'grrFormPrimitive';


/**
 * Semantic type corresponding to this directive.
 *
 * @const
 * @export
 */
exports.SemanticPrimitiveFormDirective.semantic_types = [
  'bool',                                                 // Boolean types.
  'RDFInteger', 'int', 'long', 'float',                   // Numeric types.
  'RDFString', 'basestring', 'RDFURN', 'str', 'unicode',  // String types.
  'bytes',                                                // Byte types.
  // TODO(user): check if we ever have to deal with
  // bytes type (RDFBytes is handled by grr-form-bytes).
];
