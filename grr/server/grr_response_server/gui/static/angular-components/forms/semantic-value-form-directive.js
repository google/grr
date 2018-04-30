'use strict';

goog.module('grrUi.forms.semanticValueFormDirective');
goog.module.declareLegacyNamespace();



/**
 * @type {Object<string,
 *     function(!angular.Scope, function(Object, !angular.Scope=)=):Object>}
 * Cache for templates used by semantic value directive.
 */
let templatesCache = {};

/**
 * Clears cached templates.
 *
 * @export
 */
exports.clearCaches = function() {
  templatesCache = {};
};


/**
 * Controller for SemanticValueFormDirective.
 *
 * @constructor
 * @param {!angular.Scope} $scope
 * @param {!angular.$compile} $compile
 * @param {!angular.jQuery} $element
 * @param {!grrUi.core.semanticRegistryService.SemanticRegistryService}
 *     grrSemanticFormDirectivesRegistryService
 * @ngInject
 */
exports.SemanticValueFormController = function(
    $scope, $compile, $element, grrSemanticFormDirectivesRegistryService) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @private {!angular.$compile} */
  this.compile_ = $compile;

  /** @private {!angular.jQuery} */
  this.element_ = $element;

  /** @private {angular.Scope|undefined} */
  this.elementScope_;

  /** @private {!grrUi.core.semanticRegistryService.SemanticRegistryService} */
  this.grrSemanticFormDirectivesRegistryService_ =
      grrSemanticFormDirectivesRegistryService;

  this.scope_.$watch('value.type', this.onValueTypeChange_.bind(this));
};
var SemanticValueFormController = exports.SemanticValueFormController;


/**
 * Handles value type changes.
 *
 * @param {?string} newValue
 * @private
 */
SemanticValueFormController.prototype.onValueTypeChange_ = function(newValue) {
  this.element_.html('');

  if (angular.isDefined(this.elementScope_)) {
    // Destroy element's scope so that its watchers do not fire (as this may
    // happen even if the element is removed from DOM).
    this.elementScope_.$destroy();
    this.elementScope_ = undefined;
  }

  if (angular.isUndefined(newValue)) {
    return;
  }

  var updateElement = function(tmpl) {
    if (angular.isDefined(tmpl)) {
      // Create a separate scope for the element so that we have a fine-grained
      // control over whether element's watchers are fired are not. This scope
      // will be destroyed as soon as the value type changes, meaning that
      // another element has to be constructed to edit the value.
      this.elementScope_ = this.scope_.$new();
      tmpl(this.elementScope_, function(cloned, opt_scope) {
        this.element_.append(cloned);
      }.bind(this));
    } else {
      this.element_.text('Can\'t handle type: ' + this.value['type']);
    }
  }.bind(this);

  var value = this.scope_.value;
  var template = templatesCache[value['type']];
  if (angular.isUndefined(template)) {
    this.compileSingleTypedValueTemplate_(value).then(function(template) {
      templatesCache[value['type']] = template;
      updateElement(template);
    }.bind(this));
  } else {
    updateElement(template);
  }
};

/**
 * Converts camelCaseStrings to dash-delimited-strings.
 *
 * @param {string} directiveName String to be converted.
 * @return {string} Converted string.
 * @export
 */
SemanticValueFormController.prototype.camelCaseToDashDelimited = function(
    directiveName) {
  return directiveName.replace(/([a-z\d])([A-Z])/g, '$1-$2').toLowerCase();
};


/**
 * Compiles a template for a given single value.
 *
 * @param {Object} value Value to compile the template for.
 * @return {function(!angular.Scope, function(Object,
 *     !angular.Scope=)=):Object} Compiled template.
 * @private
 */
SemanticValueFormController.prototype
    .compileSingleTypedValueTemplate_ = function(value) {

  var successHandler = function success(directive) {
    var element = angular.element('<span />');

    element.html('<' + this.camelCaseToDashDelimited(directive.directive_name) +
        ' metadata="metadata" value="value" />');
    return this.compile_(element);
  }.bind(this);

  var failureHandler = function failure() {
    var element = angular.element('<span />');

    element.html('<p class="form-control-static">No directive ' +
        'for type: {$ value.type $}.</p>');
    return this.compile_(element);
  }.bind(this);

  return this.grrSemanticFormDirectivesRegistryService_.
      findDirectiveForType(value['type']).then(
          successHandler, failureHandler);
};


/**
 * SemanticValueFormDirective renders a form corresponding to a given semantic
 * RDF type.
 *
 * @return {!angular.Directive} Directive definition object.
 */
exports.SemanticValueFormDirective = function() {
  return {
    restrict: 'E',
    scope: {
      value: '=',
      metadata: '=?'
    },
    controller: SemanticValueFormController,
    controllerAs: 'controller'
  };
};


/**
 * Name of the directive in Angular.
 *
 * @const
 * @export
 */
exports.SemanticValueFormDirective.directive_name = 'grrFormValue';
