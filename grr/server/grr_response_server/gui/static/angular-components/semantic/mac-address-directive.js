goog.module('grrUi.semantic.macAddressDirective');
goog.module.declareLegacyNamespace();



/**
 * Converts MAC address represented as bytes to a human readable representation.
 *
 * @param {string} address Byte-string with MAC address.
 * @return {string} Human-readable MAC address.
 */
const convertMacAddressToString = function(address) {
  const result = [];
  for (let i = 0; i < address.length; ++i) {
    let part = address.charCodeAt(i).toString(16);
    if (part.length === 1) {
      part = '0' + part;
    }
    result.push(part);
  }
  return result.join(':');
};



/**
 * Controller for MacAddressDirective.
 * @unrestricted
 */
const MacAddressController = class {
  /**
   * @param {!angular.Scope} $scope
   * @ngInject
   */
  constructor($scope) {
    /** @private {!angular.Scope} */
    this.scope_ = $scope;

    /** @type {string} */
    this.convertedAddress;

    this.scope_.$watch('::value', this.onValueChange.bind(this));
  }

  /**
   * Handles changes of scope.value attribute.
   *
   * @param {number} newValue Timestamp value in microseconds.
   * @suppress {missingProperties} as value can be anything.
   */
  onValueChange(newValue) {
    const address = newValue.value;
    if (angular.isString(address)) {
      this.convertedAddress = convertMacAddressToString(window.atob(address));
    } else {
      this.convertedAddress = '-';
    }
  }
};



/**
 * Directive that displays MacAddress values.
 *
 * @return {!angular.Directive} Directive definition object.
 * @ngInject
 * @export
 */
exports.MacAddressDirective = function() {
  return {
    scope: {value: '='},
    restrict: 'E',
    template: '<nobr ng-if="::controller.convertedAddress !== undefined">' +
        '{$ ::controller.convertedAddress $}</nobr>',
    controller: MacAddressController,
    controllerAs: 'controller'
  };
};


/**
 * Name of the directive in Angular.
 *
 * @const
 * @export
 */
exports.MacAddressDirective.directive_name = 'grrMacAddress';

/**
 * Semantic type corresponding to this directive.
 *
 * @const
 * @export
 */
exports.MacAddressDirective.semantic_type = 'MacAddress';
