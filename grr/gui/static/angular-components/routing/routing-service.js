'use strict';

goog.module('grrUi.routing.routingService');
goog.module.declareLegacyNamespace();



/**
 * Service for wrapping AngularUI Router. Some relevant features are only
 * in AngularUI Router 1.0+. This service mimics these features and can
 * be replaed after upgrading AngularUI Router.
 *
 * @param {!ui.router.$state} $state
 * @constructor
 * @ngInject
 * @export
 */
exports.RoutingService = function($state) {
  /** @private {!ui.router.$state} */
  this.state_ = $state;
};
var RoutingService = exports.RoutingService;


/**
 * Name of the service in Angular.
 */
RoutingService.service_name = 'grrRoutingService';

/**
 * Returns an href corresponding to a given state with given params.
 *
 * @param {string} targetState The state to transition to.
 * @param {Object=} opt_params An optional dictionary of state parameters.
 * @return {string} Href corresponding to a given state with given params.
 * @export
 */
RoutingService.prototype.href = function(targetState, opt_params) {
  return this.state_.href(targetState, opt_params);
};

/**
 * Performes a state transition to a target state.
 *
 * Remarks: This method uses the notify option to control whether state change
 * events should be fired. If notify is set to false, no events will be fired
 * and existing directives are not replaced. Instead, these directives can
 * listen to changes in the state params and update to the new URL. This is the
 * wanted behavior if the target state and the current state are identical and
 * only param values changed. If notify is set to true, the regular UI router
 * behavior is executed and will lead to a full reload of the target state (and
 * parent states, if necessary).
 *
 * @param {string} targetState The state to transition to.
 * @param {Object=} opt_params An optional dictionary of state parameters.
 * @return {!angular.$q.Promise} Promise that resolves to the result.
 * @export
 */
RoutingService.prototype.go = function(targetState, opt_params) {
  var currentState = this.state_.current.name;
  return this.state_.go(targetState, opt_params,
                        {notify: currentState !== targetState});
};

/**
 * Adds a watcher for one or more parameters. If any of the parameters change,
 * the callback is called. The callback will be called with the new value(s)
 * of the watched parameter(s) and a dictionary holding all param values,
 * not only the watched ones.
 *
 * @param {!angular.Scope} scope The scope on which to register the watcher.
 * @param {string|Array<string>} paramNames The name of the parameter.
 * @param {function(?, Object=)} callback The callback.
 * @param {boolean=} opt_stateAgnostic If this is true, the callback will be
 *     called on every URL parameters change. If opt_stateAgnostic is false,
 *     the callback will only be called if the current state is equal or
 *     is inherited from the state that was current when the callback was
 *     installed.
 *     By default this is false, as in most cases we don't want the callback
 *     to be called when we're transitioning to a new state, but the
 *     directive corresponding to the old state is still active. Example:
 *     we're in "Browse Virtual File System" and clicking on
 *     "Manage Launched Flows" navigator link. After the click the routing
 *     state is changed immediately and we don't want VFS directives (
 *     which are still active) to receive any callbacks, as they're going
 *     to be destroyed really soon.
 *
 * @return {function()} A de-registration function for this listener.
 * @export
 */
RoutingService.prototype.uiOnParamsChanged = function(
    scope, paramNames, callback, opt_stateAgnostic) {
  var currentStateName = this.state_.current.name;

  if (!angular.isArray(paramNames)) {
    // We were passed a string rather than an array. Wrap the single string in
    // an array and proceed as normal.
    var paramName = paramNames;
    paramNames = /** @type {!Array} */ ([paramName]);
  }

  return scope.$watchCollection(function() {
    return paramNames.map(function(paramName) {
      return this.state_.params[paramName];
    }.bind(this));
  }.bind(this), function(newValues, oldValues) {
    if (!opt_stateAgnostic && !this.state_.includes(currentStateName)) {
      // If opt_stateAgnostic == false, only send the callbacks if current
      // state is equal or is a child of the state that was active when the
      // callbacks were installed.
      return;
    }

    if (newValues.length === 1) {
      callback(newValues[0], this.state_.params);
    } else {
      callback(newValues, this.state_.params);
    }
  }.bind(this));
};

/**
 * Adds a watcher, which is called whenever a state change occured.
 *
 * @param {!angular.Scope} scope The scope on which to register the watcher.
 * @param {function(string, Object=)} callback The callback.
 * @return {function()} A de-registration function for this listener.
 * @export
 */
RoutingService.prototype.onStateChange = function(scope, callback) {
  // Call immediately for intialization.
  callback(this.state_.current.name, this.state_.params);

  return scope.$on('$stateChangeSuccess', function(event, state, params) {
    callback(state.name, params);
  }.bind(this));
};


