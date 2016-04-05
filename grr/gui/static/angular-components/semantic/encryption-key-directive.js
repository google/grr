'use strict';

goog.provide('grrUi.semantic.encryptionKeyDirective.EncryptionKeyController');
goog.provide('grrUi.semantic.encryptionKeyDirective.EncryptionKeyDirective');
goog.provide('grrUi.semantic.encryptionKeyDirective.stringifyEncryptionKey');

goog.scope(function() {


/**
 * Produces hex-encoded version of an encryption key.
 *
 * @param {string} base64Bytes Base64-encoded encryption key.
 * @return {string} Hex-encoded encryption key.
 */
grrUi.semantic.encryptionKeyDirective.stringifyEncryptionKey = function(
    base64Bytes) {
  var decoded = window.atob(base64Bytes);
  var result = [];
  for (var i = 0; i < decoded.length; ++i) {
    var c = decoded.charCodeAt(i).toString(16);
    if (c.length == 1) {
      c = '0' + c;
    }
    result.push(c);
  }
  return result.join('');
};


/**
 * Controller for EncryptionKeyDirective.
 *
 * @param {!angular.Scope} $scope
 * @constructor
 * @ngInject
 */
grrUi.semantic.encryptionKeyDirective.EncryptionKeyController = function(
    $scope) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @type {string} */
  this.stringifiedKey;

  this.scope_.$watch('::value.value', this.onValueChange.bind(this));
};

var EncryptionKeyController =
    grrUi.semantic.encryptionKeyDirective.EncryptionKeyController;


/**
 * Handles changes of scope.value attribute.
 *
 * @param {string} newValue New base64-encoded encryption key value.
 */
EncryptionKeyController.prototype.onValueChange = function(newValue) {
  if (angular.isDefined(newValue)) {
    this.stringifiedKey =
        grrUi.semantic.encryptionKeyDirective.stringifyEncryptionKey(
            newValue);
  }
};



/**
 * Directive that displays EncryptionKey values.
 *
 * @constructor
 * @ngInject
 * @export
 */
grrUi.semantic.encryptionKeyDirective.EncryptionKeyDirective = function() {
  return {
    scope: {
      value: '='
    },
    restrict: 'E',
    template: '{$ ::controller.stringifiedKey $}',
    controller: EncryptionKeyController,
    controllerAs: 'controller'
  };
};


/**
 * Name of the directive in Angular.
 *
 * @const
 * @export
 */
grrUi.semantic.encryptionKeyDirective.EncryptionKeyDirective.directive_name =
    'grrEncryptionKey';

/**
 * Semantic type corresponding to this directive.
 *
 * @const
 * @export
 */
grrUi.semantic.encryptionKeyDirective.EncryptionKeyDirective.semantic_type =
    'EncryptionKey';


});  // goog.scope
