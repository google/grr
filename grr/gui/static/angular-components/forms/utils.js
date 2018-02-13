'use strict';

goog.module('grrUi.forms.utils');
goog.module.declareLegacyNamespace();



/**
 * Directives in angular-components/forms render forms that allow
 * users to edit RDFValues. In GRR UI Javascript code these RDFValues
 * are represented by objects that look like {type: 'TypeName', value: X}
 * where X may either be a primitive value (a string or a number),
 * or a map with attributes set. If X is a map, then for every key-value
 * pair <K, V>, K will be a string and V will be either an array of
 * {type: ..., value: ...} objects or a nested {type: ..., value: ...} object.
 *
 * Any directive in angular-components/forms can add 'validationError'
 * annotation to the Javascript RDFValue object. This annotation
 * indicates that the user provided invalid input while editing the
 * RDFValue.
 *
 * valueHasErrors function recursively checks a given RDFValue for
 * 'validationError' annotations. This function is meant to be used
 * in UI components that have to deal with forms and have to
 * enable/disable certain elements based on the data validity.
 *
 * Example: 'Launch' button in 'Start Flow' view should be disabled
 * if flow arguments are not valid.
 *
 * @param {Object} value Value to be checked for 'validationError' annotations.
 * @return {boolean} True if the value or any of its nested values has the
 *     'validationError' annotation, false otherwise.
 */
exports.valueHasErrors = function(value) {
  if (!angular.isObject(value)) {
    return false;
  }

  if (value['validationError']) {
    return true;
  }

  if (angular.isArray(value)) {
    var alen = value.length;
    for (var i = 0; i < alen; ++i) {
      if (valueHasErrors(value[i])) {
        return true;
      }
    }

    return false;
  }

  if (angular.isObject(value['value'])) {
    var nestedValue = value['value'];
    for (var k in nestedValue) {
      if (valueHasErrors(nestedValue[k])) {
        return true;
      }
    }
  }

  return false;
};
var valueHasErrors = exports.valueHasErrors;
