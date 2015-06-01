'use strict';

goog.provide('grrUi.semantic.networkAddressDirective.NetworkAddressController');
goog.provide('grrUi.semantic.networkAddressDirective.NetworkAddressDirective');
goog.provide('grrUi.semantic.networkAddressDirective.convertIpv4AddressToString');
goog.provide('grrUi.semantic.networkAddressDirective.convertIpv6AddressToString');

goog.scope(function() {


/**
 * Converts IPv4 address represented as bytes to a human readable
 * representation.
 *
 * @param {string} address Byte-string with IPv4 address.
 * @return {string} Human-readable IPv4 address.
 */
grrUi.semantic.networkAddressDirective.convertIpv4AddressToString = function(
    address) {
  var result = [];
  for (var i = 0; i < address.length; ++i) {
    var part = address.charCodeAt(i).toString(10);
    if (part.length === 1) {
      part = '0' + part;
    }
    result.push(part);
  }
  return result.join('.');
};
var convertIpv4AddressToString =
    grrUi.semantic.networkAddressDirective.convertIpv4AddressToString;


/**
 * Converts IPv6 address represented as bytes to a human readable
 * representation.
 *
 * @param {string} address Byte-string with IPv6 address.
 * @return {string} Human-readable IPv6 address.
 */
grrUi.semantic.networkAddressDirective.convertIpv6AddressToString = function(
    address) {
  var result = [];
  var colonCounter = 0;
  for (var i = 0; i < address.length; ++i) {
    var part = address.charCodeAt(i).toString(16);
    if (part.length === 1) {
      part = '0' + part;
    }
    result.push(part);
    if (++colonCounter == 2) {
      result.push(':');
      colonCounter = 0;
    }
  }
  return result.join('');
};
var convertIpv6AddressToString =
    grrUi.semantic.networkAddressDirective.convertIpv6AddressToString;


/**
 * Converts network address represented as bytes to a human readable
 * representation.
 *
 * @param {string} address Base64-encoded with a network address.
 * @param {string} addressType INET or INET6.
 * @return {string} Human-readable IPv6 address.
 */
grrUi.semantic.networkAddressDirective.convertBase64AddressToString = function(
    address, addressType) {
  if (angular.isUndefined(address)) {
    return '-';
  } else {
    switch (addressType) {
      case 'INET':
        return convertIpv4AddressToString(window.atob(address));
      case 'INET6':
        return convertIpv6AddressToString(window.atob(address));
      default:
        return '<unknown address type>';
    }
  }
};
var convertBase64AddressToString =
    grrUi.semantic.networkAddressDirective.convertBase64AddressToString;


/**
 * Controller for NetworkAddressDirective.
 *
 * @param {!angular.Scope} $scope
 * @constructor
 * @ngInject
 */
grrUi.semantic.networkAddressDirective.NetworkAddressController = function(
    $scope) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @type {string} */
  this.convertedAddress;

  this.scope_.$watch('::value', this.onValueChange.bind(this));
};

var NetworkAddressController =
    grrUi.semantic.networkAddressDirective.NetworkAddressController;


/**
 * Handles changes of scope.value attribute.
 *
 * @param {number} newValue Timestamp value in microseconds.
 * @suppress {missingProperties} as value can be anything.
 */
NetworkAddressController.prototype.onValueChange = function(newValue) {
  if (!angular.isObject(newValue)) {
    this.convertedAddress = '-';
    return;
  }

  if (angular.isObject(newValue.value)) {
    if (angular.isDefined(newValue.value.packed_bytes)) {
      this.convertedAddress = convertBase64AddressToString(
          newValue.value.packed_bytes.value,
          newValue.value.address_type.value);
    } else if (angular.isDefined(newValue.value.human_readable)) {
      this.convertedAddress = newValue.value.human_readable.value;
    } else {
      this.convertedAddress = '<unknown>';
    }
  } else if (angular.isObject(newValue)) {
    if (angular.isDefined(newValue.packed_bytes)) {
      this.convertedAddress = convertBase64AddressToString(
          newValue.packed_bytes,
          newValue.address_type);
    } else if (angular.isDefined(newValue.human_readable)) {
      this.convertedAddress = newValue.human_readable;
    } else {
      this.convertedAddress = '<unknown>';
    }
  }
};



/**
 * Directive that displays NetworkAddress values.
 *
 * @constructor
 * @ngInject
 * @export
 */
grrUi.semantic.networkAddressDirective.NetworkAddressDirective = function() {
  return {
    scope: {
      value: '='
    },
    restrict: 'E',
    template: '<nobr ng-if="::controller.convertedAddress !== undefined">' +
        '{$ ::controller.convertedAddress $}</nobr>',
    controller: NetworkAddressController,
    controllerAs: 'controller'
  };
};


/**
 * Name of the directive in Angular.
 *
 * @const
 * @export
 */
grrUi.semantic.networkAddressDirective.NetworkAddressDirective.directive_name =
    'grrNetworkAddress';

/**
 * Semantic type corresponding to this directive.
 *
 * @const
 * @export
 */
grrUi.semantic.networkAddressDirective.NetworkAddressDirective.semantic_type =
    'NetworkAddress';

});  // goog.scope
