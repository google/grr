/*! @license Firebase v3.7.8
Build: rev-44ec95c
Terms: https://firebase.google.com/terms/ */

'use strict';

Object.defineProperty(exports, "__esModule", {
    value: true
});

var _createClass = function () { function defineProperties(target, props) { for (var i = 0; i < props.length; i++) { var descriptor = props[i]; descriptor.enumerable = descriptor.enumerable || false; descriptor.configurable = true; if ("value" in descriptor) descriptor.writable = true; Object.defineProperty(target, descriptor.key, descriptor); } } return function (Constructor, protoProps, staticProps) { if (protoProps) defineProperties(Constructor.prototype, protoProps); if (staticProps) defineProperties(Constructor, staticProps); return Constructor; }; }();

exports.createFirebaseNamespace = createFirebaseNamespace;

var _deep_copy = require('./deep_copy');

var _subscribe = require('./subscribe');

var _errors = require('./errors');

var _shared_promise = require('./shared_promise');

function _classCallCheck(instance, Constructor) { if (!(instance instanceof Constructor)) { throw new TypeError("Cannot call a class as a function"); } }

var LocalPromise = _shared_promise.local.Promise;
var DEFAULT_ENTRY_NAME = '[DEFAULT]';

var FirebaseAppImpl = function () {
    function FirebaseAppImpl(options, name, firebase_) {
        var _this = this;

        _classCallCheck(this, FirebaseAppImpl);

        this.firebase_ = firebase_;
        this.isDeleted_ = false;
        this.services_ = {};
        this.name_ = name;
        this.options_ = (0, _deep_copy.deepCopy)(options);
        var hasCredential = 'credential' in this.options_;
        var hasServiceAccount = 'serviceAccount' in this.options_;
        if (hasCredential || hasServiceAccount) {
            var deprecatedKey = hasServiceAccount ? 'serviceAccount' : 'credential';
            if (typeof console !== 'undefined') {
                console.log('The \'' + deprecatedKey + '\' property specified in the first argument ' + 'to initializeApp() is deprecated and will be removed in the next ' + 'major version. You should instead use the \'firebase-admin\' ' + 'package. See https://firebase.google.com/docs/admin/setup for ' + 'details on how to get started.');
            }
        }
        Object.keys(firebase_.INTERNAL.factories).forEach(function (serviceName) {
            var factoryName = firebase_.INTERNAL.useAsService(_this, serviceName);
            if (factoryName === null) {
                return;
            }
            var getService = _this.getService.bind(_this, factoryName);
            (0, _deep_copy.patchProperty)(_this, serviceName, getService);
        });
    }

    _createClass(FirebaseAppImpl, [{
        key: 'delete',
        value: function _delete() {
            var _this2 = this;

            return new LocalPromise(function (resolve) {
                _this2.checkDestroyed_();
                resolve();
            }).then(function () {
                _this2.firebase_.INTERNAL.removeApp(_this2.name_);
                var services = [];
                Object.keys(_this2.services_).forEach(function (serviceKey) {
                    Object.keys(_this2.services_[serviceKey]).forEach(function (instanceKey) {
                        services.push(_this2.services_[serviceKey][instanceKey]);
                    });
                });
                return LocalPromise.all(services.map(function (service) {
                    return service.INTERNAL.delete();
                }));
            }).then(function () {
                _this2.isDeleted_ = true;
                _this2.services_ = {};
            });
        }

    }, {
        key: 'getService',
        value: function getService(name, instanceString) {
            this.checkDestroyed_();
            if (typeof this.services_[name] === 'undefined') {
                this.services_[name] = {};
            }
            var instanceSpecifier = instanceString || DEFAULT_ENTRY_NAME;
            if (typeof this.services_[name][instanceSpecifier] === 'undefined') {
                var firebaseService = this.firebase_.INTERNAL.factories[name](this, this.extendApp.bind(this), instanceString);
                this.services_[name][instanceSpecifier] = firebaseService;
                return firebaseService;
            } else {
                return this.services_[name][instanceSpecifier];
            }
        }

    }, {
        key: 'extendApp',
        value: function extendApp(props) {
            (0, _deep_copy.deepExtend)(this, props);
        }

    }, {
        key: 'checkDestroyed_',
        value: function checkDestroyed_() {
            if (this.isDeleted_) {
                error('app-deleted', { 'name': this.name_ });
            }
        }
    }, {
        key: 'name',
        get: function get() {
            this.checkDestroyed_();
            return this.name_;
        }
    }, {
        key: 'options',
        get: function get() {
            this.checkDestroyed_();
            return this.options_;
        }
    }]);

    return FirebaseAppImpl;
}();

FirebaseAppImpl.prototype.name && FirebaseAppImpl.prototype.options || FirebaseAppImpl.prototype.delete || console.log("dc");
function createFirebaseNamespace() {
    var apps_ = {};
    var factories = {};
    var appHooks = {};
    var namespace = {
        '__esModule': true,
        'initializeApp':
        function (options, name) {
            if (name === undefined) {
                name = DEFAULT_ENTRY_NAME;
            } else {
                if (typeof name !== 'string' || name === '') {
                    error('bad-app-name', { 'name': name + '' });
                }
            }
            if (apps_[name] !== undefined) {
                error('duplicate-app', { 'name': name });
            }
            var app = new FirebaseAppImpl(options, name, namespace);
            apps_[name] = app;
            callAppHooks(app, 'create');
            if (app.INTERNAL == undefined || app.INTERNAL.getToken == undefined) {
                (0, _deep_copy.deepExtend)(app, {
                    INTERNAL: {
                        'getUid': function getUid() {
                            return null;
                        },
                        'getToken': function getToken() {
                            return LocalPromise.resolve(null);
                        },
                        'addAuthTokenListener': function addAuthTokenListener() {},
                        'removeAuthTokenListener': function removeAuthTokenListener() {}
                    }
                });
            }
            return app;
        }
        ,
        'app': app,
        'apps': null,
        'Promise': LocalPromise,
        'SDK_VERSION': '3.7.8',
        'INTERNAL': {
            'registerService':
            function (name, createService, serviceProperties, appHook, allowMultipleInstances) {
                if (factories[name]) {
                    error('duplicate-service', { 'name': name });
                }
                if (!!allowMultipleInstances) {
                    factories[name] = createService;
                } else {
                    factories[name] = function (app, extendApp) {
                        return createService(app, extendApp, DEFAULT_ENTRY_NAME);
                    };
                }
                if (appHook) {
                    appHooks[name] = appHook;
                }
                var serviceNamespace = void 0;
                serviceNamespace = function (appArg) {
                    if (appArg === undefined) {
                        appArg = app();
                    }
                    if (typeof appArg[name] !== 'function') {
                        error('invalid-app-argument', { 'name': name });
                    }
                    return appArg[name]();
                };
                if (serviceProperties !== undefined) {
                    (0, _deep_copy.deepExtend)(serviceNamespace, serviceProperties);
                }
                namespace[name] = serviceNamespace;
                return serviceNamespace;
            }
            ,
            'createFirebaseNamespace': createFirebaseNamespace,
            'extendNamespace': function (props) {
                (0, _deep_copy.deepExtend)(namespace, props);
            },
            'createSubscribe': _subscribe.createSubscribe,
            'ErrorFactory': _errors.ErrorFactory,
            'removeApp':
            function (name) {
                var app = apps_[name];
                callAppHooks(app, 'delete');
                delete apps_[name];
            }
            ,
            'factories': factories,
            'useAsService': useAsService,
            'Promise': _shared_promise.local.GoogPromise,
            'deepExtend': _deep_copy.deepExtend
        }
    };
    (0, _deep_copy.patchProperty)(namespace, 'default', namespace);
    Object.defineProperty(namespace, 'apps', {
        get: function () {
            return Object.keys(apps_).map(function (name) {
                return apps_[name];
            });
        }
    });function app(name) {
        name = name || DEFAULT_ENTRY_NAME;
        var result = apps_[name];
        if (result === undefined) {
            error('no-app', { 'name': name });
        }
        return result;
    }
    (0, _deep_copy.patchProperty)(app, 'App', FirebaseAppImpl);
    function callAppHooks(app, eventName) {
        Object.keys(factories).forEach(function (serviceName) {
            var factoryName = useAsService(app, serviceName);
            if (factoryName === null) {
                return;
            }
            if (appHooks[factoryName]) {
                appHooks[factoryName](eventName, app);
            }
        });
    }
    function useAsService(app, name) {
        if (name === 'serverAuth') {
            return null;
        }
        var useService = name;
        var options = app.options;
        if (name === 'auth' && (options['serviceAccount'] || options['credential'])) {
            useService = 'serverAuth';
            if (!('serverAuth' in factories)) {
                error('sa-not-supported');
            }
        }
        return useService;
    }
    return namespace;
}
function error(code, args) {
    throw appErrors.create(code, args);
}
var errors = {
    'no-app': 'No Firebase App \'{$name}\' has been created - ' + 'call Firebase App.initializeApp()',
    'bad-app-name': 'Illegal App name: \'{$name}',
    'duplicate-app': 'Firebase App named \'{$name}\' already exists',
    'app-deleted': 'Firebase App named \'{$name}\' already deleted',
    'duplicate-service': 'Firebase service named \'{$name}\' already registered',
    'sa-not-supported': 'Initializing the Firebase SDK with a service ' + 'account is only allowed in a Node.js environment. On client ' + 'devices, you should instead initialize the SDK with an api key and ' + 'auth domain',
    'invalid-app-argument': 'firebase.{$name}() takes either no argument or a ' + 'Firebase App instance.'
};
var appErrors = new _errors.ErrorFactory('app', 'Firebase', errors);
