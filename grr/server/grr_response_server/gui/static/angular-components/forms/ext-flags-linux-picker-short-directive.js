'use strict';

goog.module('grrUi.forms.extFlagsLinuxPickerShortDirective');
goog.module.declareLegacyNamespace();

const {LINUX_FLAGS_ORDERED} = goog.require('grrUi.client.extFlags');
const {TroggableFlags} = goog.require('grrUi.forms.extFlagsTroggling');


/**
 * @constructor
 * @param {!angular.Scope} $scope
 * @ngInject
 */
const ExtFlagsLinuxPickerShortController = function($scope) {
  /** @type {!TroggableFlags} */
  this.flags = new TroggableFlags(LINUX_FLAGS_ORDERED);

  $scope.$watch('bitsSet.value', (value) => {
    this.flags.bitsSet = value;
  });
  $scope.$watch('bitsUnset.value', (value) => {
    this.flags.bitsUnset = value;
  });

  $scope.$watch('controller.flags.bitsSet', (value) => {
    $scope['bitsSet']['value'] = value;
  });
  $scope.$watch('controller.flags.bitsUnset', (value) => {
    $scope['bitsUnset']['value'] = value;
  });
};

/**
 * @return {!angular.Directive} Directive definition object.
 */
const ExtFlagsLinuxPickerShortDirective = function() {
  return {
    restrict: 'E',
    scope: {
      bitsSet: '=',
      bitsUnset: '=',
    },
    templateUrl:
        '/static/angular-components/forms/ext-flags-linux-picker-short.html',
    controller: ExtFlagsLinuxPickerShortController,
    controllerAs: 'controller',
  };
};

/**
 * Name of the directive in Angular.
 *
 * @const
 * @export
 */
ExtFlagsLinuxPickerShortDirective.directive_name =
    'grrExtFlagsLinuxPickerShort';

exports.ExtFlagsLinuxPickerShortDirective = ExtFlagsLinuxPickerShortDirective;
