'use strict';

goog.module('grrUi.semantic.semanticValueDirective');
goog.module.declareLegacyNamespace();


/**
 * @type {Object<string,
 *     function(!angular.Scope, function(Object, !angular.Scope=)=):Object>}
 * Cache for templates used by semantic value directive.
 */
let singleValueTemplateCache = {};


/**
 * @type {(function(!angular.Scope, function(Object,
 *     !angular.Scope=)=):Object|undefined)}
 * Precached template for lists of values.
 */
let repeatedValuesTemplate;


/**
 * Clears cached templates.
 *
 * @export
 */
exports.clearCaches = function() {
  singleValueTemplateCache = {};
  repeatedValuesTemplate = undefined;
};

/**
 * Gets value of the cached single value template.
 *
 * @param {string} name Name of the template to lookup in the cache.
 * @return {function(!angular.Scope, function(Object, !angular.Scope=)=):Object}
 *
 * @export
 */
exports.getCachedSingleValueTemplate = function(name) {
  return singleValueTemplateCache[name];
};


/**
 * Controller for the RegistryOverrideDirective.
 *
 * @constructor
 * @param {!angular.Scope} $scope
 * @ngInject
 */
const RegistryOverrideController = function(
    $scope) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @type {Object<string, Object>} */
  this.map;

  /** @type {string} */
  this.overrideKey;

  this.scope_.$watch(function() { return this.map; }.bind(this),
                     this.onMapChange_.bind(this));
};



/**
 * Handles changes of the 'map' binding and calculates unique map identifier
 * to be used in the templates cache.
 *
 * @param {Object} newValue
 * @private
 */
RegistryOverrideController.prototype.onMapChange_ = function(newValue) {
  this.overrideKey = '';
  angular.forEach(Object.keys(/** @type {!Object} */(this.map)).sort(), function(key) {
    var value = this.map[key];
    this.overrideKey += ':' + key + '_' + value['directive_name'];
  }.bind(this));
};


/**
 * RegistryOverrideDirective allows users to override "RDF type <-> directive"
 * bindings registered in grrSemanticValueDirectivesRegistryService.
 *
 * @return {!angular.Directive} Directive definition object.
 */
exports.RegistryOverrideDirective = function() {
  return {
    scope: {
      map: '='
    },
    controller: RegistryOverrideController,
    bindToController: true,
    restrict: 'E',
    transclude: true,
    template: '<ng-transclude></ng-transclude>'
  };
};


/**
 * Directive's name in Angular.
 *
 * @const
 * @export
 */
exports.RegistryOverrideDirective.directive_name =
    'grrSemanticValueRegistryOverride';


/**
 * Controller for the SemanticValueDirective.
 *
 * @constructor
 * @param {!angular.Scope} $scope
 * @param {!angular.$compile} $compile
 * @param {!jQuery} $element
 * @param {!grrUi.core.semanticRegistryService.SemanticRegistryService}
 *     grrSemanticValueDirectivesRegistryService
 * @ngInject
 */
const SemanticValueController = function(
    $scope, $compile, $element, grrSemanticValueDirectivesRegistryService) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @type {?} */
  this.scope_.value;

  /** @private {!angular.$compile} */
  this.compile_ = $compile;

  /** @private {!jQuery} */
  this.element_ = $element;

  /** @private {!grrUi.core.semanticRegistryService.SemanticRegistryService} */
  this.grrSemanticValueDirectivesRegistryService_ =
      grrSemanticValueDirectivesRegistryService;

  /** @type {RegistryOverrideController} */
  this.registryOverrideController;

  this.scope_.$watch('::value', this.onValueChange.bind(this));
};



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

  var overrides;
  if (this.registryOverrideController) {
    overrides = this.registryOverrideController.map;
  }

  return this.grrSemanticValueDirectivesRegistryService_.
      findDirectiveForType(value['type'], overrides)
      .then(successHandler, failureHandler);
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

    // Make sure that templates for overrides do not collide with either
    // templates for other overrides or with default templates.
    var cacheKey = value['type'];
    if (this.registryOverrideController) {
      cacheKey += this.registryOverrideController.overrideKey;
    }

    template = singleValueTemplateCache[cacheKey];
    if (angular.isUndefined(template)) {
      this.compileSingleTypedValueTemplate_(value).then(function(tmpl) {
        singleValueTemplateCache[cacheKey] = tmpl;
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

    if (angular.isUndefined(repeatedValuesTemplate)) {
      repeatedValuesTemplate = this.compileRepeatedValueTemplate_();
    }
    template = repeatedValuesTemplate;

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
exports.SemanticValueDirective = function() {
  return {
    scope: {
      value: '='
    },
    require: '?^grrSemanticValueRegistryOverride',
    restrict: 'E',
    controller: SemanticValueController,
    controllerAs: 'controller',
    link: function(scope, element, attrs, grrSemanticValueRegistryOverrideCtrl) {
      if (grrSemanticValueRegistryOverrideCtrl) {
        scope['controller']['registryOverrideController'] =
            grrSemanticValueRegistryOverrideCtrl;
      }
    }
  };
};


/**
 * Directive's name in Angular.
 *
 * @const
 * @export
 */
exports.SemanticValueDirective.directive_name = 'grrSemanticValue';
