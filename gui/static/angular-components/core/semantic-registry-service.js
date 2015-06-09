'use strict';

goog.provide('grrUi.core.semanticRegistry.SemanticRegistryService');

goog.scope(function() {



/**
 * Service for registering objects by their semantic types.
 *
 * @constructor
 * @ngInject
 * @export
 */
grrUi.core.semanticRegistry.SemanticRegistryService = function() {
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
 * - And for for semantic forms.
 */
SemanticRegistryService.forms_service_name =
    'grrSemanticFormDirectivesRegistryService';

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
SemanticRegistryService.prototype.findDirectiveForMro = function(
    mro) {
  for (var i = 0; i < mro.length; ++i) {
    var objType = mro[i];
    var directive = this.directivesByType_[objType];
    if (angular.isDefined(directive)) {
      return directive;
    }
  }

  return undefined;
};

});  // goog.scope
