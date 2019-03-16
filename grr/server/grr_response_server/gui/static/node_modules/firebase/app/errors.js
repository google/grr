/*! @license Firebase v3.7.8
Build: rev-44ec95c
Terms: https://firebase.google.com/terms/ */

'use strict';

Object.defineProperty(exports, "__esModule", {
    value: true
});

var _createClass = function () { function defineProperties(target, props) { for (var i = 0; i < props.length; i++) { var descriptor = props[i]; descriptor.enumerable = descriptor.enumerable || false; descriptor.configurable = true; if ("value" in descriptor) descriptor.writable = true; Object.defineProperty(target, descriptor.key, descriptor); } } return function (Constructor, protoProps, staticProps) { if (protoProps) defineProperties(Constructor.prototype, protoProps); if (staticProps) defineProperties(Constructor, staticProps); return Constructor; }; }();

exports.patchCapture = patchCapture;

function _classCallCheck(instance, Constructor) { if (!(instance instanceof Constructor)) { throw new TypeError("Cannot call a class as a function"); } }

var ERROR_NAME = 'FirebaseError';
var captureStackTrace = Error.captureStackTrace;
function patchCapture(captureFake) {
    var result = captureStackTrace;
    captureStackTrace = captureFake;
    return result;
}

var FirebaseError = function FirebaseError(code, message) {
    _classCallCheck(this, FirebaseError);

    this.code = code;
    this.message = message;

    if (captureStackTrace) {
        captureStackTrace(this, ErrorFactory.prototype.create);
    } else {
        var err = Error.apply(this, arguments);
        this.name = ERROR_NAME;
        Object.defineProperty(this, 'stack', {
            get: function get() {
                return err.stack;
            }
        });
    }
};


FirebaseError.prototype = Object.create(Error.prototype);
FirebaseError.prototype.constructor = FirebaseError;
FirebaseError.prototype.name = ERROR_NAME;

var ErrorFactory = exports.ErrorFactory = function () {
    function ErrorFactory(service, serviceName, errors) {
        _classCallCheck(this, ErrorFactory);

        this.service = service;
        this.serviceName = serviceName;
        this.errors = errors;
        this.pattern = /\{\$([^}]+)}/g;
    }

    _createClass(ErrorFactory, [{
        key: 'create',
        value: function create(code, data) {
            if (data === undefined) {
                data = {};
            }
            var template = this.errors[code];
            var fullCode = this.service + '/' + code;
            var message = void 0;
            if (template === undefined) {
                message = "Error";
            } else {
                message = template.replace(this.pattern, function (match, key) {
                    var value = data[key];
                    return value !== undefined ? value.toString() : '<' + key + '?>';
                });
            }
            message = this.serviceName + ': ' + message + ' (' + fullCode + ').';
            var err = new FirebaseError(fullCode, message);
            for (var prop in data) {
                if (!data.hasOwnProperty(prop) || prop.slice(-1) === '_') {
                    continue;
                }
                err[prop] = data[prop];
            }
            return err;
        }
    }]);

    return ErrorFactory;
}();
