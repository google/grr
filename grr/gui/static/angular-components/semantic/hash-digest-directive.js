'use strict';

goog.provide('grrUi.semantic.hashDigestDirective.HashDigestController');
goog.provide('grrUi.semantic.hashDigestDirective.HashDigestDirective');

goog.scope(function() {


/**
 * Controller for HashDigestDirective.
 *
 * @param {!angular.Scope} $scope
 * @param {!angular.$window} $window
 * @constructor
 * @ngInject
 */
grrUi.semantic.hashDigestDirective.HashDigestController = function(
    $scope, $window) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @private {!angular.$window} */
  this.window_ = $window;

  /** @type {string} */
  this.stringifiedBytes;

  this.scope_.$watch('::value', this.onValueChange.bind(this));
};

var HashDigestController =
    grrUi.semantic.hashDigestDirective.HashDigestController;


/**
 * Encodes given bytes string to a hex-encoded string.
 *
 * @param {string} bytes Bytes string.
 * @return {string} Hex-encoded string.
 */
HashDigestController.prototype.bytesToHexString = function(bytes){
  var hex = '';
  for(var i = 0; i < bytes.length; i += 1) {
    var char = bytes.charCodeAt(i).toString(16);
    hex += ('0' + char).substr(-2); // add leading zero if necessary
  }
  return hex;
};


/**
 * Handles changes of scope.value attribute.
 *
 * @param {number} newValue Timestamp value in microseconds.
 * @suppress {missingProperties} as value can be anything.
 */
HashDigestController.prototype.onValueChange = function(newValue) {
  var bytes = newValue.value;
  if (angular.isString(bytes)) {
    try {
      this.stringifiedBytes = this.bytesToHexString(this.window_.atob(bytes));
    } catch (err) {
      this.stringifiedBytes = 'base64decodeerror(' + err.message + '):' + bytes;
    }
  } else {
    this.stringifiedBytes = '';
  }
};



/**
 * Directive that displays a HashDigest value.
 *
 * @constructor
 * @ngInject
 * @export
 */
grrUi.semantic.hashDigestDirective.HashDigestDirective = function() {
  return {
    scope: {
      value: '='
    },
    restrict: 'E',
    template: '<nobr ng-if="::controller.stringifiedBytes !== undefined">' +
        '{$ ::controller.stringifiedBytes $}</nobr>',
    controller: HashDigestController,
    controllerAs: 'controller'
  };
};


/**
 * Name of the directive in Angular.
 *
 * @const
 * @export
 */
grrUi.semantic.hashDigestDirective.HashDigestDirective.directive_name =
    'grrHashDigest';

/**
 * Semantic type corresponding to this directive.
 *
 * @const
 * @export
 */
grrUi.semantic.hashDigestDirective.HashDigestDirective.semantic_type =
    'HashDigest';


});  // goog.scope
