'use strict';

goog.module('grrUi.core.bytesToHexFilter');
goog.module.declareLegacyNamespace();



/**
 * Converts the input bytes to a hex string representation.
 *
 * @param {string} bytes String representation of the input bytes.
 * @return {string} Hex string representation of the input bytes.
 */
const filterImplementation = function(bytes) {
  var hex = '';
  for(var i = 0; i < bytes.length; i += 1) {
    var char = bytes.charCodeAt(i).toString(16);
    hex += ('0' + char).substr(-2); // add leading zero if necessary
  }
  return hex;
};

/**
 * Angular filter definition.
 *
 * @return {!Function}
 * @export
 * @ngInject
 */
exports.BytesToHexFilter = function() {
  return function(input) {
    return filterImplementation(input);
  };
};


/**
 * Name of the filter in Angular.
 *
 * @const
 * @export
 */
exports.BytesToHexFilter.filter_name = 'grrBytesToHex';
