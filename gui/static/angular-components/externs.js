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
 * @param {string} renderer
 * @param {string} domId
 * @param {Object=} opt_state
 *     the AJAX request (as query parameters).
 * @param {Function=} opt_onSuccess
 *     completion.
 */
grr.layout = function(renderer, domId, opt_state, opt_onSuccess) {};


/**
 * @type {Object<string, string>}
 */
grr.hash;


/**
 * @param {string} name
 * @param {string} value
 * @param {?} event
 * @param {Object=} opt_data
 */
grr.publish = function(name, value, event, opt_data) {};

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
 *   dismiss: function(string),
 *   result: angular.$q.Promise
 *   }}
 */
angularUi.$modalInstance;


/**
 * @typedef {{
 *   open: function(Object): angularUi.$modalInstance
 *   }}
 */
angularUi.$modal;


/**
 * @param {(jQuerySelector|Element|jQuery|string)} placeholder
 * @param {Array} data
 * @param {Object=} options
 */
$.plot = function(placeholder, data, options) {};
