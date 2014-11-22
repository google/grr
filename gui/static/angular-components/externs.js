/**
 * @param {string} module
 * @return {Function}
 */
var minErr = function(module) { return function() {}; };


/**
 * @param {!angular.JQLite} element
 * @return {string} Returns the string representation of the element.
 */
var startingTag = function(element) { return ''; };


/**
 * @type {Object}
 * @const
 */
var grr = {};


/**
 * @param {string} hash
 */
grr.loadFromHash = function(hash) {};


/**
 * Angular UI definitions.
 */


/**
 * @type {Object}
 * @const
 */
var angularUi = {};


/**
 * @typedef {{
 *   close: function(string),
 *   dismiss: function(string)
 *   }}
 */
angularUi.$modalInstance;


/**
 * @typedef {{
 *   open: function(Object): angularUi.$modalInstance
 *   }}
 */
angularUi.$modal;
