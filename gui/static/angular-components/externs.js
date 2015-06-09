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
 * @type {Object}
 */
grr.labels_completer = {};


/**
 * @param {(jQuerySelector|Element|jQuery|string)} element
 * @param {Array<string>} completions
 * @param {RegExp} regex
 */
grr.labels_completer.Completer = function(element, completions, regex) {};


/**
 * @type {Object<string, string>}
 */
grr.hash;


/**
 * @type {Object<string, string>}
 */
grr.state;


/**
 * @param {string} name
 * @param {string} value
 * @param {?} opt_event
 * @param {Object=} opt_data
 */
grr.publish = function(name, value, opt_event, opt_data) {};


/**
 * Angular definitions.
 */

/**
 * @typedef {{
 *   get: function(string)
 *   }}
 */
angular.$cookies;



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
 * @param {Object=} opt_options
 */
$.plot = function(placeholder, data, opt_options) {};
