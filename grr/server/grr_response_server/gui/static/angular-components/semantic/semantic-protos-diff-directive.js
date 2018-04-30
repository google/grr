'use strict';

goog.module('grrUi.semantic.semanticProtosDiffDirective');
goog.module.declareLegacyNamespace();

const {SemanticDiffAnnotatedProtoDirective} = goog.require('grrUi.semantic.semanticDiffAnnotatedProtoDirective');
const {SemanticProtoDirective} = goog.require('grrUi.semantic.semanticProtoDirective');



/**
 * Adds '_diff' annotations to items inside two arrays.
 * The algorithm employed is very simplistic, but should suffice for
 * GRR needs:
 * - An item is considered added if it's present in the
 * newValue array, but not in the originalValue array.
 * - An item is considered removed if it's present in the
 * originalValue array, but not in the newValue array.
 *
 * Cases of duplicate items are not handled and the order of items
 * is not respected. 'changed' annotation is never set.
 *
 * @param {Array<Object>} originalValue
 * @param {Array<Object>} newValue
 */
var diffAnnotateArrays = function(originalValue, newValue) {
  angular.forEach(originalValue, function(originalItem) {
    var found = false;
    angular.forEach(newValue, function(newItem) {
      if (angular.equals(originalItem, newItem)) {
        found = true;
      }
    });

    if (!found) {
      originalItem['_diff'] = 'removed';
    }
  });

  angular.forEach(newValue, function(newItem) {
    var found = false;
    angular.forEach(originalValue, function(originalItem) {
      if (angular.equals(originalItem, newItem)) {
        found = true;
      }
    });

    if (!found) {
      newItem['_diff'] = 'added';
    }
  });
};

/**
 * Annotates two given RDFValue-based data structures with diff annotations.
 * RDFValues are represented by objects that look like
 * {type: 'TypeName', value: X} where X may either be a primitive value
 * (a string or a number), or a map with attributes set. If X is a map,
 * then for every key-value pair <K, V>, K will be a string and V will
 * be either an array of {type: ..., value: ...} objects or a nested
 * {type: ..., value: ...} object.
 *
 * diffAnnotate recursively adds a '_diff' key to {type: ..., value: ...}
 * data structures and also to array elements inside the given values. '_diff'
 * key is added if the algorithm considers a certain attribute or an array item
 * of the given values to be added, removed or changed.
 *
 * Added _diff keys are used by grr-semantic-diff-annotated-proto directive
 * to render the values with differently colored attributes (depending on
 * whether they were added, removed or changed).
 *
 * @param {Object|Array<Object>|undefined} originalValue
 * @param {Object|Array<Object>|undefined} newValue
 *
 * @export
 */
exports.diffAnnotate = function(originalValue, newValue) {
  if (angular.isUndefined(originalValue) && angular.isUndefined(newValue)) {
    return;
  }

  // If originalValue is undefined, then newValue was added to the parent
  // data structure.
  //
  // See the case handled below when both newValue and originalValue are
  // nested objects and where diffAnnotate is called recursively to
  // annotate them.
  if (angular.isUndefined(originalValue)) {
    newValue['_diff'] = 'added';
    return;
  }

  // If newValue is undefined, then originalValue was removed from the parent
  // data structure.
  //
  // See the case handled below when both newValue and originalValue are
  // nested objects and where diffAnnotate is called recursively to
  // annotate them.
  if (angular.isUndefined(newValue)) {
    originalValue['_diff'] = 'removed';
    return;
  }

  // At this point both newValue and originalValue are guaranteed to be
  // defined. Given how RDF data structures are represented and given this
  // function's implementation, at this point newValue and originalValue
  // can only be Arrays or Objects with key-value properties set (i.e. maps).

  // First we handle the case when both newValue and originalValue are arrays
  // or just one of them is an array.
  if ((angular.isArray(originalValue) && !angular.isArray(newValue)) ||
      (!angular.isArray(originalValue) && angular.isArray(newValue))) {
    // Although the case of an attribute changing its type from an array to
    // something else is next to impossible, let's handle it cleanly.
    //
    // Either originalValue or newValue is an array here. We're intentionally
    // adding '_diff' key to an array, since:
    // a) JS treats arrays as objects and has no problems with adding a
    //    custom key to it.
    // b) This key will be seen and respected by
    //    grr-semantic-diff-annotated-proto directive used to display
    //    data structures processed by diffAnnotate.
    originalValue['_diff'] = newValue['_diff'] = 'changed';
    return;
  }

  if (angular.isArray(originalValue) && angular.isArray(newValue)) {
    // See diffAnnotateArrays for details on how arrays are diffed.
    diffAnnotateArrays(/** @type {Array<Object>} */(originalValue),
        /** @type {Array<Object>} */(newValue));
    return;
  }

  // At this point both originalValue and newValue are guaranteed to be
  // maps with key-value properties set. We expect them to have a structure of
  // {type: 'TypeName', value: X} where X may either be a primitive value
  // (a string or a number), or a map with attributes set. If X is a map,
  // then for every key-value pair <K, V>, K will be a string and V will
  // be either an array of {type: ..., value: ...} objects or a nested
  // {type: ..., value: ...} object. This is a representation of RDFValues
  // that we use throughout the code and which is returned by the
  // grrApiService.


  // If type of the value has changed, it means that the value has changed.
  if (originalValue['type'] != newValue['type']) {
    originalValue['_diff'] = newValue['_diff'] = 'changed';
    return;
  }

  // If originalValue's value was a primitive and it's not equal to
  // newValue's value, it means that the value has changed.
  if (angular.isString(originalValue['value']) ||
      angular.isNumber(originalValue['value'])) {
    if (!angular.equals(originalValue['value'], newValue['value'])) {
      originalValue['_diff'] = newValue['_diff'] = 'changed';
    }
    return;
  }

  // At this point both values' "value" attribute is guaranteed to be a map
  // (see comments above). We build a union of both maps so that
  // we can traverse the union of the keys.
  var allKeys = angular.extend({}, originalValue['value'], newValue['value']);
  // For every key present in either one of two values, call diffAnnotate
  // recursively. originalValue['value'][key] and newValue['value'][key]
  // can either be undefined, be arrays or be objects of a
  // {type: ..., value: ...} structure.
  for (var key in allKeys) {
    diffAnnotate(originalValue['value'][key], newValue['value'][key]);
  }
};
var diffAnnotate = exports.diffAnnotate;

/**
 * Controller for SemanticProtosDiffDirective.
 *
 * @param {!angular.Scope} $scope
 * @constructor
 * @ngInject
 */
const SemanticProtosDiffController = function(
    $scope) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @type {Object} */
  this.annotatedOriginalValue;

  /** @type {Object} */
  this.annotatedNewValue;

  var protoType = SemanticProtoDirective.semantic_type;
  var protoDirectiveOverride = SemanticDiffAnnotatedProtoDirective;

  /** @type {Object<string, Object>} */
  this.overrideMap = {};
  this.overrideMap[protoType] = protoDirectiveOverride;

  this.scope_.$watchGroup(['originalValue', 'newValue'],
                          this.onValuesChange_.bind(this));
};



/**
 * Handles changes of directive's bindings.
 *
 * @private
 */
SemanticProtosDiffController.prototype.onValuesChange_ = function() {
  if (angular.isUndefined(this.scope_['originalValue']) ||
      angular.isUndefined(this.scope_['newValue'])) {
    return;
  }

  this.annotatedOriginalValue = angular.copy(this.scope_['originalValue']);
  this.annotatedNewValue = angular.copy(this.scope_['newValue']);
  diffAnnotate(this.annotatedOriginalValue, this.annotatedNewValue);
};


/**
 * Directive that displays a diff between two semantic protos.
 *
 * @return {angular.Directive} Directive definition object.
 * @ngInject
 * @export
 */
exports.SemanticProtosDiffDirective = function() {
  return {
    scope: {
      originalValue: '=',
      newValue: '=',
      visibleFields: '=',
      hiddenFields: '='
    },
    restrict: 'E',
    templateUrl: '/static/angular-components/semantic/' +
        'semantic-protos-diff.html',
    controller: SemanticProtosDiffController,
    controllerAs: 'controller'
  };
};


/**
 * Name of the directive in Angular.
 *
 * @const
 * @export
 */
exports.SemanticProtosDiffDirective.directive_name = 'grrSemanticProtosDiff';
