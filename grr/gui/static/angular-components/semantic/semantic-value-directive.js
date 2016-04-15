'use strict';

goog.provide('grrUi.semantic.semanticValueDirective');
goog.provide('grrUi.semantic.semanticValueDirective.SemanticValueController');
goog.provide('grrUi.semantic.semanticValueDirective.SemanticValueDirective');
goog.provide('grrUi.semantic.semanticValueDirective.clearCaches');

goog.scope(function() {


/**
 * @type {Object<string,
 *     function(!angular.Scope, function(Object, !angular.Scope=)=):Object>}
 * Cache for templates used by semantic value directive.
 */
grrUi.semantic.semanticValueDirective.singleValueTemplateCache = {};


/**
 * @type {(function(!angular.Scope, function(Object,
 *     !angular.Scope=)=):Object|undefined)}
 * Precached template for lists of values.
 */
grrUi.semantic.semanticValueDirective.repeatedValuesTemplate;


/**
 * Clears cached templates.
 *
 * @export
 */
grrUi.semantic.semanticValueDirective.clearCaches = function() {
  grrUi.semantic.semanticValueDirective.singleValueTemplateCache = {};
  grrUi.semantic.semanticValueDirective.repeatedValuesTemplate = undefined;
};



/**
 * Controller for the SemanticValueDirective.
 *
 * @constructor
 * @param {!angular.Scope} $scope
 * @param {!angular.$compile} $compile
 * @param {!jQuery} $element
 * @param {!grrUi.core.semanticRegistry.SemanticRegistryService}
 *     grrSemanticValueDirectivesRegistryService
 * @ngInject
 */
grrUi.semantic.semanticValueDirective.SemanticValueController = function(
    $scope, $compile, $element, grrSemanticValueDirectivesRegistryService) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @type {?} */
  this.scope_.value;

  /** @private {!angular.$compile} */
  this.compile_ = $compile;

  /** @private {!jQuery} */
  this.element_ = $element;

  /** @private {!grrUi.core.semanticRegistry.SemanticRegistryService} */
  this.grrSemanticValueDirectivesRegistryService_ =
      grrSemanticValueDirectivesRegistryService;

  this.scope_.$watch('::value', this.onValueChange.bind(this));
};

var SemanticValueController =
    grrUi.semantic.semanticValueDirective.SemanticValueController;


/**
 * Converts camelCaseStrings to dash-delimited-strings.
 *
 * @param {string} directiveName String to be converted.
 * @return {string} Converted string.
 */
SemanticValueController.prototype.camelCaseToDashDelimited = function(
    directiveName) {
  return directiveName.replace(/\W+/g, '-')
      .replace(/([a-z\d])([A-Z])/g, '$1-$2').toLowerCase();
};


/**
 * Compiles a template for a given single value.
 *
 * @param {Object} value Value to compile the template for.
 * @return {!angular.$q.Promise} Promise that will get resolved into the
 *     compiled template.
 * @private
 */
SemanticValueController.prototype.compileSingleTypedValueTemplate_ = function(
    value) {
  var successHandler = function(directive) {
    var element = angular.element('<span />');

    element.html('<' +
        this.camelCaseToDashDelimited(directive.directive_name) +
        ' value="::value" />');
    return this.compile_(element);
  }.bind(this);

  var failureHandler = function(directive) {
    var element = angular.element('<span />');
    element.html('{$ ::value.value $}');
    return this.compile_(element);
  }.bind(this);

  return this.grrSemanticValueDirectivesRegistryService_.
      findDirectiveForType(value['type']).then(successHandler, failureHandler);
};


/**
 * Compiles a template for repeated values.
 *
 * @return {function(!angular.Scope, function(Object,
 *     !angular.Scope=)=):Object} Compiled template.
 * @private
 */
SemanticValueController.prototype.compileRepeatedValueTemplate_ = function() {
  var element = angular.element(
      '<div ng-repeat="item in ::repeatedValue || []">' +
          '<grr-semantic-value value="::item" /></div>');
  return this.compile_(element);
};


/**
 * Handles value changes.
 *
 * @export
 */
SemanticValueController.prototype.onValueChange = function() {
  var value = this.scope_.value;

  if (value == null) {
    return;
  }

  /**
   * @type {(function(!angular.Scope, function(Object,
   *     !angular.Scope=)=):Object|undefined)}
   */
  var template;


  if (angular.isDefined(value['type'])) {
    var handleTemplate = function(template) {
      template(this.scope_, function(cloned, opt_scope) {
        this.element_.html('');
        this.element_.append(cloned);
      }.bind(this));
    }.bind(this);

    var singleValueTemplateCache = grrUi.semantic.semanticValueDirective
        .singleValueTemplateCache;

    template = singleValueTemplateCache[value['type']];
    if (angular.isUndefined(template)) {
      this.compileSingleTypedValueTemplate_(value).then(function(tmpl) {
        singleValueTemplateCache[value['type']] = tmpl;
        handleTemplate(tmpl);
      }.bind(this));
    } else {
      handleTemplate(template);
    }
  } else if (angular.isArray(value)) {
    if (value.length > 10) {
      var continuation = value.slice(10);
      this.scope_.repeatedValue = value.slice(0, 10);
      this.scope_.repeatedValue.push({
        type: '__FetchMoreLink',
        value: continuation
      });
    } else {
      this.scope_.repeatedValue = value;
    }

    if (angular.isUndefined(
        grrUi.semantic.semanticValueDirective.repeatedValuesTemplate)) {
      grrUi.semantic.semanticValueDirective.repeatedValuesTemplate =
          this.compileRepeatedValueTemplate_();
    }
    template = grrUi.semantic.semanticValueDirective.repeatedValuesTemplate;

    template(this.scope_, function(cloned, opt_scope) {
      this.element_.html('');
      this.element_.append(cloned);
    }.bind(this));
  } else {
    this.element_.text(value.toString() + ' ');
  }
};


/**
 * SemanticValueDirective renders given RDFValue by applying type-specific
 * renderers to its fields. It's assumed that RDFValue is fetched with
 * type info information.
 *
 * @return {!angular.Directive} Directive definition object.
 */
grrUi.semantic.semanticValueDirective.SemanticValueDirective = function() {
  return {
    scope: {
      value: '='
    },
    restrict: 'E',
    controller: SemanticValueController,
    controllerAs: 'controller'
  };
};


/**
 * Directive's name in Angular.
 *
 * @const
 * @export
 */
grrUi.semantic.semanticValueDirective.SemanticValueDirective.directive_name =
    'grrSemanticValue';

});  // goog.scope
