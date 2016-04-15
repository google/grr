'use strict';

goog.provide('grrUi.core.semanticRegistry.SemanticRegistryService');

goog.scope(function() {



/**
 * Service for registering objects by their semantic types.
 *
 * @constructor
 * @param {!angular.$q} $q
 * @param {!grrUi.core.reflectionService.ReflectionService} grrReflectionService
 * @ngInject
 * @export
 */
grrUi.core.semanticRegistry.SemanticRegistryService = function(
    $q, grrReflectionService) {
  /** @private {!angular.$q} */
  this.q_ = $q;

  /** @private {!grrUi.core.reflectionService.ReflectionService} */
  this.grrReflectionService_ = grrReflectionService;

  /** @private {!Object<string, Object>} */
  this.directivesByType_ = {};
};
var SemanticRegistryService =
    grrUi.core.semanticRegistry.SemanticRegistryService;


/**
 * The implemented service is used as 3 separate singletons:
 * - For semantic value presentation directives.
 */
SemanticRegistryService.values_service_name =
    'grrSemanticValueDirectivesRegistryService';

/**
 * - And for semantic forms.
 */
SemanticRegistryService.forms_service_name =
    'grrSemanticFormDirectivesRegistryService';

/**
 * - And for semantic forms.
 */
SemanticRegistryService.repeated_forms_service_name =
    'grrSemanticRepeatedFormDirectivesRegistryService';

/**
 * - And for output plugins directvies.
 */
SemanticRegistryService.output_plugins_service_name =
    'grrOutputPluginsDirectivesRegistryService';


/**
 * Registers given directive, associates it with a given type.
 *
 * @param {string} type RDFValue type rendered by this directive.
 * @param {!Object} directive Any object representing the directive.
 * @export
 */
SemanticRegistryService.prototype.registerDirective = function(
    type, directive) {
  this.directivesByType_[type] = directive;
};


/**
 * Returns most specific directive for a given MRO.
 *
 * @param {!Array<string>} mro MRO of an object to be rendered by the directive.
 * @return {Object|undefined} An object representing found directive, or
 *     undefined if nothing was found.
 * @export
 */
SemanticRegistryService.prototype.findDirectiveForMro = function(mro) {
  for (var i = 0; i < mro.length; ++i) {
    var objType = mro[i];
    var directive = this.directivesByType_[objType];
    if (angular.isDefined(directive)) {
      return directive;
    }
  }

  return undefined;
};

/**
 * Returns directive for a given value type.
 *
 * @param {string} type Type of an object to be rendered by the directive.
 * @return {!angular.$q.Promise} Promise that resolves to the found directive or
 *     rejects otherwise.
 * @export
 */
SemanticRegistryService.prototype.findDirectiveForType = function(type) {
  // If we have an exact match, no need for the MRO check.
  if (angular.isDefined(this.directivesByType_[type])) {
    var deferred = this.q_.defer();
    deferred.resolve(this.directivesByType_[type]);
    return deferred.promise;
  }

  var handleDescriptor = function(descriptor) {
    var directive = this.findDirectiveForMro(descriptor['mro']);
    if (angular.isDefined(directive)) {
      return directive;
    } else {
      return this.q_.reject(new Error('No directive found.'));
    }
  }.bind(this);

  return this.grrReflectionService_.getRDFValueDescriptor(type)
      .then(handleDescriptor); // TODO(user): handle failure scenarios
                               // in grrReflectionService.
};


});  // goog.scope
