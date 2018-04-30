'use strict';

goog.module('grrUi.forms.semanticProtoRepeatedFieldFormDirective');
goog.module.declareLegacyNamespace();

const {camelCaseToDashDelimited} = goog.require('grrUi.core.utils');



/**
 * Controller for SemanticProtoRepeatedFieldFormDirective.
 *
 * @constructor
 * @param {!angular.Scope} $scope
 * @param {!angular.jQuery} $element
 * @param {!angular.$compile} $compile
 * @param {!grrUi.core.semanticRegistryService.SemanticRegistryService}
 *     grrSemanticRepeatedFormDirectivesRegistryService
 * @ngInject
 */
const SemanticProtoRepeatedFieldFormController = function(
        $scope, $element, $compile,
        grrSemanticRepeatedFormDirectivesRegistryService) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @private {!angular.jQuery} */
  this.element_ = $element;

  /** @private {!angular.$compile} */
  this.compile_ = $compile;

  /** @private {!grrUi.core.semanticRegistryService.SemanticRegistryService} */
  this.grrSemanticRepeatedFormDirectivesRegistryService_ =
      grrSemanticRepeatedFormDirectivesRegistryService;

  /** @export {boolean} */
  this.hasCustomTemplate;

  /** @export {boolean} */
  this.hideCustomTemplateLabel;

  this.scope_.$watchGroup(['field', 'descriptor', 'value'],
                          this.onFieldDescriptorChange_.bind(this));
};



/**
 * Handles changes in field and descriptor.
 *
 * @private
 */
SemanticProtoRepeatedFieldFormController.prototype.onFieldDescriptorChange_ =
    function() {
  if (angular.isDefined(this.scope_['field']) &&
      angular.isDefined(this.scope_['descriptor']) &&
      angular.isDefined(this.scope_['value'])) {

    if (this.scope_['noCustomTemplate']) {
      this.onCustomDirectiveNotFound_();
    } else {
      this.grrSemanticRepeatedFormDirectivesRegistryService_.
          findDirectiveForType(this.scope_['descriptor']['mro'][0]).then(
              this.onCustomDirectiveFound_.bind(this),
              this.onCustomDirectiveNotFound_.bind(this));
    }
  }
};


/**
 * Handles cases when a custom directive that handles this type of repeated
 * values is not found.
 *
 * @private
 */
SemanticProtoRepeatedFieldFormController.prototype.onCustomDirectiveNotFound_ = function() {
  this.hasCustomTemplate = false;
};


/**
 * Handles cases when a custom directive that handles this type of repeated
 * values is found.
 *
 * @param {Object} directive Found directive.
 * @private
 */
SemanticProtoRepeatedFieldFormController.prototype.onCustomDirectiveFound_ = function(directive) {
  this.hasCustomTemplate = true;
  this.hideCustomTemplateLabel = directive['hideCustomTemplateLabel'];

  var element = angular.element('<span />');

  element.html('<' + camelCaseToDashDelimited(directive.directive_name) +
      ' descriptor="descriptor" value="value" field="field" />');
  var template = this.compile_(element);

  var customTemplateElement;
  if (this.hideCustomTemplateLabel) {
    customTemplateElement = this.element_.find(
        'div[name="custom-template-without-label"]');
  } else {
    customTemplateElement = this.element_.find(
        'div[name="custom-template"]');
  }

  customTemplateElement.html('');

  template(this.scope_, function(cloned, opt_scope) {
    customTemplateElement.append(cloned);
  }.bind(this));
};


/**
 * Handles clicks on 'Add' button.
 *
 * @export
 */
SemanticProtoRepeatedFieldFormController.prototype.addItem = function() {
  this.scope_.value.splice(0, 0,
                           angular.copy(this.scope_['descriptor']['default']));
};


/**
 * Handles clicks on 'Remove' buttons.
 *
 * @param {number} index Index of the element to remove.
 * @export
 */
SemanticProtoRepeatedFieldFormController.prototype.removeItem = function(
    index) {
  this.scope_.value.splice(index, 1);
};


/**
 * SemanticProtoRepeatedFieldFormDirective renders a form corresponding to a
 * repeated field of a RDFProtoStruct.
 *
 * @return {!angular.Directive} Directive definition object.
 */
exports.SemanticProtoRepeatedFieldFormDirective = function() {
  return {
    scope: {
      value: '=',
      descriptor: '=',
      field: '=',
      noCustomTemplate: '='
    },
    restrict: 'E',
    templateUrl: '/static/angular-components/forms/' +
        'semantic-proto-repeated-field-form.html',
    controller: SemanticProtoRepeatedFieldFormController,
    controllerAs: 'controller'
  };
};


/**
 * Name of the directive in Angular.
 *
 * @const
 * @export
 */
exports.SemanticProtoRepeatedFieldFormDirective.directive_name =
    'grrFormProtoRepeatedField';
