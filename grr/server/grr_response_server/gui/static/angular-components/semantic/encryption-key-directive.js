goog.module('grrUi.semantic.encryptionKeyDirective');
goog.module.declareLegacyNamespace();



/**
 * Produces hex-encoded version of an encryption key.
 *
 * @param {string} base64Bytes Base64-encoded encryption key.
 * @return {string} Hex-encoded encryption key.
 */
exports.stringifyEncryptionKey = function(base64Bytes) {
  const decoded = window.atob(base64Bytes);
  const result = [];
  for (let i = 0; i < decoded.length; ++i) {
    let c = decoded.charCodeAt(i).toString(16);
    if (c.length == 1) {
      c = '0' + c;
    }
    result.push(c);
  }
  return result.join('');
};


/**
 * Controller for EncryptionKeyDirective.
 * @unrestricted
 */
const EncryptionKeyController = class {
  /**
   * @param {!angular.Scope} $scope
   * @ngInject
   */
  constructor($scope) {
    /** @private {!angular.Scope} */
    this.scope_ = $scope;

    /** @type {string} */
    this.stringifiedKey;

    this.scope_.$watch('::value.value', this.onValueChange.bind(this));
  }

  /**
   * Handles changes of scope.value attribute.
   *
   * @param {string} newValue New base64-encoded encryption key value.
   */
  onValueChange(newValue) {
    if (angular.isDefined(newValue)) {
      this.stringifiedKey = exports.stringifyEncryptionKey(newValue);
    }
  }
};



/**
 * Directive that displays EncryptionKey values.
 *
 * @return {!angular.Directive} Directive definition object.
 * @ngInject
 * @export
 */
exports.EncryptionKeyDirective = function() {
  return {
    scope: {value: '='},
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
exports.EncryptionKeyDirective.directive_name = 'grrEncryptionKey';

/**
 * Semantic type corresponding to this directive.
 *
 * @const
 * @export
 */
exports.EncryptionKeyDirective.semantic_type = 'EncryptionKey';
