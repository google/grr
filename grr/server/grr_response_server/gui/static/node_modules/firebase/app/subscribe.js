/*! @license Firebase v3.7.8
Build: rev-44ec95c
Terms: https://firebase.google.com/terms/ */

'use strict';

Object.defineProperty(exports, "__esModule", {
    value: true
});

var _typeof = typeof Symbol === "function" && typeof Symbol.iterator === "symbol" ? function (obj) { return typeof obj; } : function (obj) { return obj && typeof Symbol === "function" && obj.constructor === Symbol && obj !== Symbol.prototype ? "symbol" : typeof obj; };

var _createClass = function () { function defineProperties(target, props) { for (var i = 0; i < props.length; i++) { var descriptor = props[i]; descriptor.enumerable = descriptor.enumerable || false; descriptor.configurable = true; if ("value" in descriptor) descriptor.writable = true; Object.defineProperty(target, descriptor.key, descriptor); } } return function (Constructor, protoProps, staticProps) { if (protoProps) defineProperties(Constructor.prototype, protoProps); if (staticProps) defineProperties(Constructor, staticProps); return Constructor; }; }();

exports.createSubscribe = createSubscribe;
exports.async = async;

var _shared_promise = require('./shared_promise');

function _classCallCheck(instance, Constructor) { if (!(instance instanceof Constructor)) { throw new TypeError("Cannot call a class as a function"); } }

var LocalPromise = _shared_promise.local.Promise;
function createSubscribe(executor, onNoObservers) {
    var proxy = new ObserverProxy(executor, onNoObservers);
    return proxy.subscribe.bind(proxy);
}

var ObserverProxy = function () {
    function ObserverProxy(executor, onNoObservers) {
        var _this = this;

        _classCallCheck(this, ObserverProxy);

        this.observers = [];
        this.unsubscribes = [];
        this.observerCount = 0;
        this.task = LocalPromise.resolve();
        this.finalized = false;
        this.onNoObservers = onNoObservers;
        this.task.then(function () {
            executor(_this);
        }).catch(function (e) {
            _this.error(e);
        });
    }

    _createClass(ObserverProxy, [{
        key: 'next',
        value: function next(value) {
            this.forEachObserver(function (observer) {
                observer.next(value);
            });
        }
    }, {
        key: 'error',
        value: function error(_error) {
            this.forEachObserver(function (observer) {
                observer.error(_error);
            });
            this.close(_error);
        }
    }, {
        key: 'complete',
        value: function complete() {
            this.forEachObserver(function (observer) {
                observer.complete();
            });
            this.close();
        }

    }, {
        key: 'subscribe',
        value: function subscribe(nextOrObserver, error, complete) {
            var _this2 = this;

            var observer = void 0;
            if (nextOrObserver === undefined && error === undefined && complete === undefined) {
                throw new Error("Missing Observer.");
            }
            if (implementsAnyMethods(nextOrObserver, ['next', 'error', 'complete'])) {
                observer = nextOrObserver;
            } else {
                observer = {
                    next: nextOrObserver,
                    error: error,
                    complete: complete
                };
            }
            if (observer.next === undefined) {
                observer.next = noop;
            }
            if (observer.error === undefined) {
                observer.error = noop;
            }
            if (observer.complete === undefined) {
                observer.complete = noop;
            }
            var unsub = this.unsubscribeOne.bind(this, this.observers.length);
            if (this.finalized) {
                this.task.then(function () {
                    try {
                        if (_this2.finalError) {
                            observer.error(_this2.finalError);
                        } else {
                            observer.complete();
                        }
                    } catch (e) {
                    }
                });
            }
            this.observers.push(observer);
            return unsub;
        }

    }, {
        key: 'unsubscribeOne',
        value: function unsubscribeOne(i) {
            if (this.observers === undefined || this.observers[i] === undefined) {
                return;
            }
            delete this.observers[i];
            this.observerCount -= 1;
            if (this.observerCount === 0 && this.onNoObservers !== undefined) {
                this.onNoObservers(this);
            }
        }
    }, {
        key: 'forEachObserver',
        value: function forEachObserver(fn) {
            if (this.finalized) {
                return;
            }
            for (var i = 0; i < this.observers.length; i++) {
                this.sendOne(i, fn);
            }
        }

    }, {
        key: 'sendOne',
        value: function sendOne(i, fn) {
            var _this3 = this;

            this.task.then(function () {
                if (_this3.observers !== undefined && _this3.observers[i] !== undefined) {
                    try {
                        fn(_this3.observers[i]);
                    } catch (e) {
                        if (typeof console !== "undefined" && console.error) {
                            console.error(e);
                        }
                    }
                }
            });
        }
    }, {
        key: 'close',
        value: function close(err) {
            var _this4 = this;

            if (this.finalized) {
                return;
            }
            this.finalized = true;
            if (err !== undefined) {
                this.finalError = err;
            }
            this.task.then(function () {
                _this4.observers = undefined;
                _this4.onNoObservers = undefined;
            });
        }
    }]);

    return ObserverProxy;
}();


function async(fn, onError) {
    return function () {
        for (var _len = arguments.length, args = Array(_len), _key = 0; _key < _len; _key++) {
            args[_key] = arguments[_key];
        }

        LocalPromise.resolve(true).then(function () {
            fn.apply(undefined, args);
        }).catch(function (error) {
            if (onError) {
                onError(error);
            }
        });
    };
}
function implementsAnyMethods(obj, methods) {
    if ((typeof obj === 'undefined' ? 'undefined' : _typeof(obj)) !== 'object' || obj === null) {
        return false;
    }
    var _iteratorNormalCompletion = true;
    var _didIteratorError = false;
    var _iteratorError = undefined;

    try {
        for (var _iterator = methods[Symbol.iterator](), _step; !(_iteratorNormalCompletion = (_step = _iterator.next()).done); _iteratorNormalCompletion = true) {
            var method = _step.value;

            if (method in obj && typeof obj[method] === 'function') {
                return true;
            }
        }
    } catch (err) {
        _didIteratorError = true;
        _iteratorError = err;
    } finally {
        try {
            if (!_iteratorNormalCompletion && _iterator.return) {
                _iterator.return();
            }
        } finally {
            if (_didIteratorError) {
                throw _iteratorError;
            }
        }
    }

    return false;
}
function noop() {
}
