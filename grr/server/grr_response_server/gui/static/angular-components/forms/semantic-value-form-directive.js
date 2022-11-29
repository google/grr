goog.module('grrUi.forms.semanticValueFormDirective');
goog.module.declareLegacyNamespace();

const semanticRegistryService = goog.requireType('grrUi.core.semanticRegistryService');



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
 * @unrestricted
 */
exports.SemanticValueFormController = class {
  /**
   * @param {!angular.Scope} $scope
   * @param {!angular.$compile} $compile
   * @param {!angular.jQuery} $element
   * @param {!semanticRegistryService.SemanticRegistryService}
   *     grrSemanticFormDirectivesRegistryService
   * @ngInject
   */
  constructor(
      $scope, $compile, $element, grrSemanticFormDirectivesRegistryService) {
    /** @private {!angular.Scope} */
    this.scope_ = $scope;

    /** @private {!angular.$compile} */
    this.compile_ = $compile;

    /** @private {!angular.jQuery} */
    this.element_ = $element;

    /** @private {angular.Scope|undefined} */
    this.elementScope_;

    /**
     * @private {!semanticRegistryService.SemanticRegistryService}
     */
    this.grrSemanticFormDirectivesRegistryService_ =
        grrSemanticFormDirectivesRegistryService;

    this.scope_.$watch('value.type', this.onValueTypeChange_.bind(this));
  }

  /**
   * Handles value type changes.
   *
   * @param {?string} newValue
   * @private
   */
  onValueTypeChange_(newValue) {
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

    const updateElement = function(tmpl) {
      if (angular.isDefined(tmpl)) {
        // Create a separate scope for the element so that we have a
        // fine-grained control over whether element's watchers are fired are
        // not. This scope will be destroyed as soon as the value type changes,
        // meaning that another element has to be constructed to edit the value.
        this.elementScope_ = this.scope_.$new();
        tmpl(this.elementScope_, function(cloned, opt_scope) {
          this.element_.append(cloned);
        }.bind(this));
      } else {
        this.element_.text('Can\'t handle type: ' + this.value['type']);
      }
    }.bind(this);

    const value = this.scope_.value;
    const template = templatesCache[value['type']];
    if (angular.isUndefined(template)) {
      this.compileSingleTypedValueTemplate_(value).then(function(template) {
        templatesCache[value['type']] = template;
        updateElement(template);
      }.bind(this));
    } else {
      updateElement(template);
    }
  }

  /**
   * Converts camelCaseStrings to dash-delimited-strings.
   *
   * @param {string} directiveName String to be converted.
   * @return {string} Converted string.
   * @export
   */
  camelCaseToDashDelimited(directiveName) {
    return directiveName.replace(/([a-z\d])([A-Z])/g, '$1-$2').toLowerCase();
  }

  /**
   * Compiles a template for a given single value.
   *
   * @param {Object} value Value to compile the template for.
   * @return {!angular.$q.Promise} Promise for compiled template.
   * @private
   */
  compileSingleTypedValueTemplate_(value) {
    const successHandler = function success(directive) {
      const element = angular.element('<span />');

      element.html(
          '<' + this.camelCaseToDashDelimited(directive.directive_name) +
          ' metadata="metadata" value="value" />');
      return this.compile_(element);
    }.bind(this);

    const failureHandler = function failure() {
      const element = angular.element('<span />');

      element.html(
          '<p class="form-control-static">No directive ' +
          'for type: {$ value.type $}.</p>');
      return this.compile_(element);
    }.bind(this);

    return this.grrSemanticFormDirectivesRegistryService_
        .findDirectiveForType(value['type'])
        .then(successHandler, failureHandler);
  }
};
const SemanticValueFormController = exports.SemanticValueFormController;



/**
 * SemanticValueFormDirective renders a form corresponding to a given semantic
 * RDF type.
 *
 * @return {!angular.Directive} Directive definition object.
 */
exports.SemanticValueFormDirective = function() {
  return {
    restrict: 'E',
    scope: {value: '=', metadata: '=?'},
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
