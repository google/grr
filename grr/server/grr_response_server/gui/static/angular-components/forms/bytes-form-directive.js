'use strict';

goog.module('grrUi.forms.bytesFormDirective');
goog.module.declareLegacyNamespace();



/**
 * Encodes given bytes string to a hex-encoded string.
 * See https://mathiasbynens.be/notes/javascript-escapes#hexadecimal
 * for details.
 *
 * @param {string} bytes Bytes string.
 * @return {string} Hex-encoded string. Only characters with codes
 *     below than 32 and greater than 126 get encoded
 */
exports.bytesToHexEncodedString = function(bytes) {
  var segmentStart = 0;
  var str = [];

  var blen = bytes.length;
  for (var i = 0; i < blen; i += 1) {
    var c = bytes.charCodeAt(i);

    if (c < 32 || c > 126) {
      var segmentLength = i - segmentStart;
      if (segmentLength > 0) {
        str.push(bytes.substr(segmentStart, segmentLength));
      }
      segmentStart = i + 1;

      var hc = c.toString(16);
      if (hc.length == 1) {
        hc = '0' + hc;
      }
      str.push('\\x' + hc);
    }
  }

  segmentLength = blen - segmentStart;
  if (segmentLength > 0) {
    str.push(bytes.substr(segmentStart, segmentLength));
  }

  return str.join('');
};
var bytesToHexEncodedString = exports.bytesToHexEncodedString;



/**
 * Decodes given hex-encoded string into a bytes string.
 *
 * @param {string} str Hex-encoded string. Not every character has
 *     to be hex-encoded. Not encoded characters are preserved as they
 *     are.
 * @return {string} Bytes string.
 */
exports.hexEncodedStringToBytes = function(str) {
  return str.replace(/\\x([0-9A-Fa-f]{2})/g, function() {
    return String.fromCharCode(parseInt(arguments[1], 16));
  });
};
var hexEncodedStringToBytes = exports.hexEncodedStringToBytes;


/**
 * Checks if the string is a byte string: i.e. that it has no unicode
 * characters.
 *
 * @param {string} str String to be checked.
 * @return {boolean} True, if the string is a byte string, false otherwise.
 */
exports.isByteString = function(str) {
  var blen = str.length;
  for (var i = 0; i < blen; i += 1) {
    var c = str.charCodeAt(i);
    if (c >= 256) {
      return false;
    }
  }

  return true;
};
var isByteString = exports.isByteString;


/**
 * Controller for BytesFormDirective.
 *
 * @constructor
 * @param {!angular.Scope} $scope
 * @param {!angular.$window} $window
 * @ngInject
 */
const BytesFormController = function(
    $scope, $window) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @private {!angular.$window} */
  this.window_ = $window;

  /** @export {string} */
  this.valueString = '';

  this.scope_.$watch('value.value',
                     this.onValueChange_.bind(this));
  this.scope_.$watch('controller.valueString',
                     this.onValueStringChange_.bind(this));
};


/**
 * Handles changes in the value bound to be edited by this directive.
 * As the value may be changed in onValueStringChange handler (i.e. when
 * user types a symbol), we're only changing this.valueString if
 * the bytes sequence it represents is different from newValue.
 *
 * @param {string} newValue New time value.
 * @private
 */
BytesFormController.prototype.onValueChange_ = function(newValue) {
  if (angular.isString(newValue)) {
    try {
      var base64DecodedBytes = this.window_.atob(newValue);
      if (base64DecodedBytes != hexEncodedStringToBytes(this.valueString)) {
        this.valueString = bytesToHexEncodedString(base64DecodedBytes);
      }
    } catch (err) {
      this.valueString = '';
    }
  }
};

/**
 * Handles changes in string representation of the time value being edited.
 * Called when user types or deletes a symbol. Updates the actual value
 * that's bound to this directive via "value" binding.
 *
 * @param {string} newValue New string from the text input.
 * @private
 */
BytesFormController.prototype.onValueStringChange_ = function(newValue) {
  if (angular.isUndefined(newValue)) {
    return;
  }

  if (!isByteString(newValue)) {
    // Annotate the value with 'validationError' annotation.
    // These annotations are meant to be used by the higher-level
    // UI components to disable submit buttons and show errors
    // summary.
    this.scope_['value']['validationError'] =
        'Unicode characters are not allowed in a byte string.';
    return;
  } else {
    delete this.scope_['value']['validationError'];
  }

  this.scope_['value']['value'] =
      this.window_.btoa(hexEncodedStringToBytes(newValue));
};


/**
 * BytesFormDirective renders RDFBytes values..
 *
 * @return {!angular.Directive} Directive definition object.
 */
exports.BytesFormDirective = function() {
  return {
    restrict: 'E',
    scope: {
      value: '=',
      metadata: '='
    },
    templateUrl: '/static/angular-components/forms/bytes-form.html',
    controller: BytesFormController,
    controllerAs: 'controller'
  };
};


/**
 * Name of the directive in Angular.
 *
 * @const
 * @export
 */
exports.BytesFormDirective.directive_name = 'grrFormBytes';

/**
 * Semantic types corresponding to this directive.
 *
 * @const
 * @export
 */
exports.BytesFormDirective.semantic_type = 'RDFBytes';
