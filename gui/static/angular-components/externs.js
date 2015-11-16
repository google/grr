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
 * @type {Object}
 */
grr.glob_completer = {};


/**
 * @param {(jQuerySelector|Element|jQuery|string)} element
 * @param {Array<string>} completions
 */
grr.glob_completer.Completer = function(element, completions) {};


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
 * A jQuery object that has been extended with Angular's extra methods.
 * @typedef {(jQuery|angular.JQLite)}
 */
angular.jQuery;


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
 *   close: function(string=),
 *   dismiss: function(string=),
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


/**
 * @param {Object} data
 */
jQuery.prototype.jstree = function(data) {};


/**
 * @type {Function}
 */
moment.utc = function() {};

/**
 * @param {number} n
 * @param {string=} opt_unit
 */
moment.duration = function(n, opt_unit) {};

/**
 * @typedef {{
 *   as: function(string):number,
 *   asSeconds: function():number,
 *   humanize: function(boolean=):string
 * }}
 */
moment.Duration;
