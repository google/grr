'use strict';

goog.provide('grrUi.forms.semanticProtoRepeatedFieldFormDirective.SemanticProtoRepeatedFieldFormController');
goog.provide('grrUi.forms.semanticProtoRepeatedFieldFormDirective.SemanticProtoRepeatedFieldFormDirective');

goog.require('grrUi.forms.semanticValueFormDirective.SemanticValueFormController');

/**
 * Controller for SemanticProtoRepeatedFieldFormDirective.
 *
 * @constructor
 * @param {!angular.Scope} $scope
 * @param {!angular.jQuery} $element
 * @param {!angular.$compile} $compile
 * @param {!grrUi.core.semanticRegistry.SemanticRegistryService}
 *     grrSemanticRepeatedFormDirectivesRegistryService
 * @ngInject
 */
grrUi.forms.semanticProtoRepeatedFieldFormDirective
    .SemanticProtoRepeatedFieldFormController = function(
        $scope, $element, $compile,
        grrSemanticRepeatedFormDirectivesRegistryService) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @private {!angular.jQuery} */
  this.element_ = $element;

  /** @private {!angular.$compile} */
  this.compile_ = $compile;

  /** @private {!grrUi.core.semanticRegistry.SemanticRegistryService} */
  this.grrSemanticRepeatedFormDirectivesRegistryService_ =
      grrSemanticRepeatedFormDirectivesRegistryService;

  /** @export {boolean} */
  this.hasCustomTemplate;

  this.scope_.$watchGroup(['field', 'descriptor'],
                          this.onFieldDescriptorChange_.bind(this));
};

var SemanticProtoRepeatedFieldFormController =
    grrUi.forms.semanticProtoRepeatedFieldFormDirective
    .SemanticProtoRepeatedFieldFormController;


/**
 * Handles changes in field and descriptor.
 *
 * @private
 */
SemanticProtoRepeatedFieldFormController.prototype.onFieldDescriptorChange_ =
    function() {
  this.hasCustomTemplate = false;
  if (angular.isDefined(this.scope_['field']) &&
      angular.isDefined(this.scope_['descriptor'])) {

    this.grrSemanticRepeatedFormDirectivesRegistryService_.
        findDirectiveForType(this.scope_['descriptor']['mro'][0]).then(
            this.onCustomDirective_.bind(this));
  }
};


/**
 * Converts camelCaseStrings to dash-delimited-strings.
 *
 * @param {string} directiveName String to be converted.
 * @return {string} Converted string.
 * @export
 */
SemanticProtoRepeatedFieldFormController.prototype.camelCaseToDashDelimited =
    function(directiveName) {
  return directiveName.replace(/([a-z\d])([A-Z])/g, '$1-$2').toLowerCase();
};


/**
 * Handles cases when a custom directive that handles this type of repeated
 * values is found.
 *
 * @param {Object} directive Found directive.
 * @private
 */
SemanticProtoRepeatedFieldFormController.prototype.onCustomDirective_ =
    function(directive) {
  this.hasCustomTemplate = true;

  var element = angular.element('<span />');

  element.html('<' + this.camelCaseToDashDelimited(directive.directive_name) +
      ' descriptor="descriptor" value="value" />');
  var template = this.compile_(element);

  var customTemplateElement = this.element_.find('div[name="custom-template"]');
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
                           angular.copy(this.scope_.descriptor['default']));
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
grrUi.forms.semanticProtoRepeatedFieldFormDirective
    .SemanticProtoRepeatedFieldFormDirective = function() {
  return {
    scope: {
      value: '=',
      descriptor: '=',
      field: '='
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
grrUi.forms.semanticProtoRepeatedFieldFormDirective
    .SemanticProtoRepeatedFieldFormDirective.directive_name =
    'grrFormProtoRepeatedField';
