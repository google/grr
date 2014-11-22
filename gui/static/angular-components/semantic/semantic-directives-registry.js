'use strict';

goog.provide('grrUi.semantic.SemanticDirectivesRegistry');

goog.scope(function() {


/**
 * @private
 */
grrUi.semantic.SemanticDirectivesRegistry.directivesByType_ = {};


/**
 * Registers given directive, associates it with a given type.
 *
 * @param {string} type RDFValue type rendered by this directive.
 * @param {!Object} directive Any object representing the directive.
 * @export
 */
grrUi.semantic.SemanticDirectivesRegistry.registerDirective =
    function(type, directive) {
  grrUi.semantic.SemanticDirectivesRegistry.directivesByType_[type] =
      directive;
};


/**
 * Returns most specific directive for a given MRO.
 *
 * @param {!Array<string>} mro MRO of an object to be rendered by the directive.
 * @return {Object|undefined} An object representing found directive, or
 *     undefined if nothing was found.
 * @export
 */
grrUi.semantic.SemanticDirectivesRegistry.findDirectiveForMro =
    function(mro) {
  for (var i = 0; i < mro.length; ++i) {
    var objType = mro[i];
    var directive =
        grrUi.semantic.SemanticDirectivesRegistry.directivesByType_[
        objType];
    if (angular.isDefined(directive)) {
      return directive;
    }
  }

  return undefined;
};


/**
 * Clears the registry.
 * @param {Object} directives Object previously returned from a call to this
 *     method. Passing this object allows user to restore
 *     previous state of the registry.
 * @return {!Object} Current set of directives. This object can be later passed
 *     the clear() method to restore previous state of the registry.
 * @export
 */
grrUi.semantic.SemanticDirectivesRegistry.clear = function(directives) {
  var returnValue = grrUi.semantic.SemanticDirectivesRegistry.directivesByType_;

  if (angular.isDefined(directives)) {
    grrUi.semantic.SemanticDirectivesRegistry.directivesByType_ = directives;
  } else {
    grrUi.semantic.SemanticDirectivesRegistry.directivesByType_ = {};
  }

  return returnValue;
};

});  // goog.scope
