'use strict';

goog.provide('grrUi.forms.semanticPrimitiveFormDirective');
goog.provide('grrUi.forms.semanticPrimitiveFormDirective.SemanticPrimitiveFormController');
goog.provide('grrUi.forms.semanticPrimitiveFormDirective.SemanticPrimitiveFormDirective');


/**
 * Controller for SemanticPrimitiveFormDirective.
 *
 * @constructor
 * @param {!angular.Scope} $scope
 * @ngInject
 */
grrUi.forms.semanticPrimitiveFormDirective.SemanticPrimitiveFormController =
    function($scope) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @export {?string} */
  this.valueType;

  this.scope_.$watch('value.type', this.onValueTypeChange_.bind(this));
};
var SemanticPrimitiveFormController =
    grrUi.forms.semanticPrimitiveFormDirective.SemanticPrimitiveFormController;


/**
 * Handles changes of the value type.
 *
 * @param {?string} newValue
 * @private
 */
SemanticPrimitiveFormController.prototype.onValueTypeChange_ = function(
    newValue) {
  if (angular.isUndefined(newValue)) {
    this.valueType = undefined;
    return;
  }

  var allowedTypes = grrUi.forms.semanticPrimitiveFormDirective
      .SemanticPrimitiveFormDirective.semantic_types;
  var typeIndex = -1;
  angular.forEach(allowedTypes,
                  function(type) {
                    var index = this.scope_.value['mro'].indexOf(type);
                    if (index != -1 && (typeIndex == -1 || typeIndex > index)) {
                      typeIndex = index;
                      this.valueType = type;
                    }
                  }.bind(this));

  if (!this.valueType) {
    this.valueType = 'RDFString';
  }
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
                       'RDFInteger', 'int',
                       'RDFString', 'basestring'];
