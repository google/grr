'use strict';

goog.provide('grrUi.semantic.macAddressDirective.MacAddressDirective');
goog.provide('grrUi.semantic.macAddressDirective.convertMacAddressToString');

goog.require('grrUi.semantic.SemanticDirectivesRegistry');

goog.scope(function() {


/**
 * Converts MAC address represented as bytes to a human readable representation.
 *
 * @param {string} address Byte-string with MAC address.
 * @return {string} Human-readable MAC address.
 */
grrUi.semantic.macAddressDirective.convertMacAddressToString = function(
    address) {
  var result = [];
  for (var i = 0; i < address.length; ++i) {
    var part = address.charCodeAt(i).toString(16);
    if (part.length === 1) {
      part = '0' + part;
    }
    result.push(part);
  }
  return result.join(':');
};
var convertMacAddressToString =
    grrUi.semantic.macAddressDirective.convertMacAddressToString;



/**
 * Directive that displays MacAddress values.
 *
 * @constructor
 * @ngInject
 * @export
 */
grrUi.semantic.macAddressDirective.MacAddressDirective = function() {
  return {
    scope: {
      value: '='
    },
    restrict: 'E',
    template: '<nobr ng-if="value">{{ convertedAddress }}</nobr>',
    link: function(scope, element) {
      scope.$watch('value', function() {
        var address;
        if (angular.isObject(scope.value)) {
          address = scope.value.value;
        } else {
          address = scope.value;
        }

        if (angular.isUndefined(address)) {
          scope.convertedAddress = '-';
        } else {
          scope.convertedAddress = convertMacAddressToString(
              window.atob(address));
        }
      });
    }
  };
};


/**
 * Name of the directive in Angular.
 */
grrUi.semantic.macAddressDirective.MacAddressDirective.directive_name =
    'grrMacAddress';

grrUi.semantic.SemanticDirectivesRegistry.registerDirective(
    'MacAddress',
    grrUi.semantic.macAddressDirective.MacAddressDirective);


});  // goog.scope
