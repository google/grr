'use strict';

goog.provide('grrUi.semantic.bytesDirective.BytesController');
goog.provide('grrUi.semantic.bytesDirective.BytesDirective');
goog.require('grrUi.forms.bytesFormDirective.bytesToHexEncodedString');

goog.scope(function() {


/**
 * Controller for BytesDirective.
 *
 * @param {!angular.Scope} $scope
 * @param {!angular.$window} $window
 * @constructor
 * @ngInject
 */
grrUi.semantic.bytesDirective.BytesController = function(
    $scope, $window) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @private {!angular.$window} */
  this.window_ = $window;

  /** @type {string} */
  this.stringifiedBytes;

  this.scope_.$watch('::value', this.onValueChange.bind(this));
};

var BytesController =
    grrUi.semantic.bytesDirective.BytesController;


/**
 * @const {number} Maximum number of bytes to render without showing a link.
 */
var FIRST_RENDER_LIMIT = 1024;


BytesController.prototype.onClick = function(e) {
  // onClick event should not be handleded by
  // anything other than this, otherwise the click
  // could be interpreted in the wrong way,
  // e.g. page could be redirected.
  e.stopPropagation();

  var bytes = this.scope_['value']['value'];
  try {
    this.stringifiedBytes =
        grrUi.forms.bytesFormDirective.bytesToHexEncodedString(
            this.window_.atob(bytes));
  } catch (err) {
    this.stringifiedBytes = 'base64decodeerror(' + err.message + '):' + bytes;
  }
};

/**
 * Handles changes of scope.value attribute.
 *
 * @param {number} newValue Timestamp value in microseconds.
 * @suppress {missingProperties} as value can be anything.
 */
BytesController.prototype.onValueChange = function(newValue) {
  var bytes = newValue.value;
  if (angular.isString(bytes)) {
    if (bytes.length < FIRST_RENDER_LIMIT) {
      try {
        this.stringifiedBytes =
            grrUi.forms.bytesFormDirective.bytesToHexEncodedString(
                this.window_.atob(bytes));
      } catch (err) {
        this.stringifiedBytes = 'base64decodeerror(' + err.message + '):' + bytes;
      }
    }
  } else {
    this.stringifiedBytes = '';
  }
};



/**
 * Directive that displays Bytes values.
 *
 * @constructor
 * @ngInject
 * @export
 */
grrUi.semantic.bytesDirective.BytesDirective = function() {
  return {
    scope: {
      value: '='
    },
    restrict: 'E',
    templateUrl: '/static/angular-components/semantic/bytes.html',
    controller: BytesController,
    controllerAs: 'controller'
  };
};


/**
 * Name of the directive in Angular.
 *
 * @const
 * @export
 */
grrUi.semantic.bytesDirective.BytesDirective.directive_name =
    'grrBytes';

/**
 * Semantic type corresponding to this directive.
 *
 * @const
 * @export
 */
grrUi.semantic.bytesDirective.BytesDirective.semantic_type =
    'RDFBytes';


});  // goog.scope
