'use strict';

goog.module('grrUi.semantic.rekall.rekallRegistryService');
goog.module.declareLegacyNamespace();



/**
 * Service for registering Rekall objects by their types.
 *
 * @constructor
 * @ngInject
 * @export
 */
exports.RekallRegistryService = function() {
  /** @private {!Object<string, Object>} */
  this.directivesByType_ = {};
};
var RekallRegistryService = exports.RekallRegistryService;

RekallRegistryService.service_name = 'grrRekallDirectivesRegistryService';


/**
 * Registers given directive, associates it with a given type.
 *
 * @param {string} type type rendered by this directive.
 * @param {!Object} directive Any object representing the directive.
 * @export
 */
RekallRegistryService.prototype.registerDirective = function(type, directive) {
  this.directivesByType_[type] = directive;
};


/**
 * Returns the most specific directive for a given MRO.
 *
 * @param {string|undefined} mro colon-separated MRO of an object to be
 *     rendered.
 * @return {Object|undefined} An object representing found directive, or
 *     undefined if nothing was found.
 * @export
 */
RekallRegistryService.prototype.findDirectiveForMro = function(mro) {
  if (angular.isUndefined(mro)) {
    return undefined;
  }

  var splittedMro = mro.split(':');

  for (var i = 0; i < splittedMro.length; ++i) {
    var objType = splittedMro[i];
    var directive = this.directivesByType_[objType];
    if (angular.isDefined(directive)) {
      return directive;
    }
  }

  return undefined;
};
