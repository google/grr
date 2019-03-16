/*! @license Firebase v3.7.8
Build: rev-44ec95c
Terms: https://firebase.google.com/terms/ */

/**
 * @fileoverview Firebase namespace and Firebase App API - INTERNAL methods.
 * @externs
 */

/**
 * @param {string} name Service name
 * @param {!firebase.ServiceFactory} createService
 * @param {Object=} serviceProperties
 * @param {(function(string, !firebase.app.App): void)=} appHook
 * @param {boolean=} allowMultipleInstances Whether the service registered
 *   supports multiple instances on the same app.
 * @return {firebase.ServiceNamespace}
 */
firebase.INTERNAL.registerService = function(
    name, createService, serviceProperties, appHook, allowMultipleInstances) {};

/** @param {!Object} props */
firebase.INTERNAL.extendNamespace = function(props) {};

firebase.INTERNAL.resetNamespace = function() {};

/** @interface */
firebase.Observer = function() {};
/** @param {*} value */
firebase.Observer.prototype.next = function(value) {};
/** @param {!Error} error */
firebase.Observer.prototype.error = function(error) {};
firebase.Observer.prototype.complete = function() {};

/** @typedef {function(*): void} */
firebase.NextFn;
/** @typedef {function(!Error): void} */
firebase.ErrorFn;
/** @typedef {function(): void} */
firebase.CompleteFn;

/** @typedef {function(): void} */
firebase.Unsubscribe;

/**
 * @typedef {function((firebase.NextFn|firebase.Observer)=,
 *                    firebase.ErrorFn=,
 *                    firebase.CompleteFn=): firebase.Unsubscribe}
 */
firebase.Subscribe;

/**
 * @param {function (!firebase.Observer): void} executor
 * @param {(function (!firebase.Observer): void)=} onNoObservers
 * @return {!firebase.Subscribe}
 */
firebase.INTERNAL.createSubscribe = function(executor, onNoObservers) {};

/**
 * @param {*} target
 * @param {*} source
 */
firebase.INTERNAL.deepExtend = function(target, source) {};

/** @param {string} name */
firebase.INTERNAL.removeApp = function(name) {};

/**
 * @type {!Object<string,
 *                function(!firebase.app.App,
 *                         (function(!Object): void)=,
 *                         string=): firebase.Service>}
 */
firebase.INTERNAL.factories = {};

/**
 * @param {!firebase.app.App} app
 * @param {string} serviceName
 * @return {string|null}
 */
firebase.INTERNAL.useAsService = function(app, serviceName) {};

/**
 * @constructor
 * @param {string} service All lowercase service code (e.g., 'auth')
 * @param {string} serviceName Display service name (e.g., 'Auth')
 * @param {!Object<string, string>} errors
 */
firebase.INTERNAL.ErrorFactory = function(service, serviceName, errors) {};

/**
 * @param {string} code
 * @param {Object=} data
 * @return {!firebase.FirebaseError}
 */
firebase.INTERNAL.ErrorFactory.prototype.create = function(code, data) {};


/** @interface */
firebase.Service = function() {}

/** @type {!firebase.app.App} */
firebase.Service.prototype.app;

/** @type {!Object} */
firebase.Service.prototype.INTERNAL;

/** @return {firebase.Promise<void>} */
firebase.Service.prototype.INTERNAL.delete = function() {};

/**
 * @typedef {function(!firebase.app.App,
 *                    !function(!Object): void,
 *                    string=): !firebase.Service}
 */
firebase.ServiceFactory;


/** @interface */
firebase.ServiceNamespace = function() {};

/**
 * Given an (optional) app, return the instance of the service
 * associated with that app.
 *
 * @param {firebase.app.App=} app
 * @return {!firebase.Service}
 */
firebase.ServiceNamespace.prototype.app = function(app) {}

/**
 * Firebase App.INTERNAL methods - default implementations in firebase-app,
 * replaced by Auth ...
 */

/**
 * Listener for an access token.
 *
 * Should pass null when the user current user is no longer value (signed
 * out or credentials become invalid).
 *
 * Firebear does not currently auto-refresh tokens, BTW - but this interface
 * would support that in the future.
 *
 * @typedef {function(?string): void}
 */
firebase.AuthTokenListener;

/**
 * Returned from app.INTERNAL.getToken().
 *
 * @typedef {{
 *   accessToken: (string)
 * }}
 */
firebase.AuthTokenData;


/** @type {!Object} */
firebase.app.App.prototype.INTERNAL;


/**
 * app.INTERNAL.getUid()
 *
 * @return {?string}
 */
firebase.app.App.prototype.INTERNAL.getUid = function() {};


/**
 * app.INTERNAL.getToken()
 *
 * @param {boolean=} forceRefresh Whether to force sts token refresh.
 * @return {!Promise<?firebase.AuthTokenData>}
 */
firebase.app.App.prototype.INTERNAL.getToken = function(forceRefresh) {};


/**
 * Adds an auth state listener.
 *
 * @param {!firebase.AuthTokenListener} listener The auth state listener.
 */
firebase.app.App.prototype.INTERNAL.addAuthTokenListener =
    function(listener) {};


/**
 * Removes an auth state listener.
 *
 * @param {!firebase.AuthTokenListener} listener The auth state listener.
 */
firebase.app.App.prototype.INTERNAL.removeAuthTokenListener =
    function(listener) {};