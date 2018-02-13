'use strict';

goog.module('grrUi.core.hexNumberFilter');
goog.module.declareLegacyNamespace();



/**
 * Converts the input number to a hex string representation.
 *
 * @param {number} input Number to show as hex string.
 * @return {string} Hex string representation of the input number. The return value is always
      a multiple of eight (with leading zeros if necessary) starting with 0x, e.g. 0x001234ff.
 */
const filterImplementation = function(input) {
  var hex = input.toString(16);

  var targetLength = Math.ceil(hex.length / 8) * 8;
  var leadingZeros = Array(targetLength - hex.length + 1).join(0);

  return '0x' + leadingZeros + hex;
};

/**
 * Angular filter definition.
 *
 * @return {!Function}
 * @export
 * @ngInject
 */
exports.HexNumberFilter = function() {
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
exports.HexNumberFilter.filter_name = 'grrHexNumber';
