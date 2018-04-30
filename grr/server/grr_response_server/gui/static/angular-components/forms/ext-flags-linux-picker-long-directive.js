'use strict';

goog.module('grrUi.forms.extFlagsLinuxPickerLongDirective');
goog.module.declareLegacyNamespace();

const {LINUX_FLAGS_ORDERED} = goog.require('grrUi.client.extFlags');
const {TroggableFlags} = goog.require('grrUi.forms.extFlagsTroggling');


/**
 * @constructor
 * @param {!angular.Scope} $scope
 * @ngInject
 */
const ExtFlagsLinuxPickerLongController = function($scope) {
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
const ExtFlagsLinuxPickerLongDirective = function() {
  return {
    restrict: 'E',
    scope: {
      bitsSet: '=',
      bitsUnset: '=',
    },
    templateUrl:
        '/static/angular-components/forms/ext-flags-linux-picker-long.html',
    controller: ExtFlagsLinuxPickerLongController,
    controllerAs: 'controller',
  };
};

/**
 * Name of the directive in Angular.
 *
 * @const
 * @export
 */
ExtFlagsLinuxPickerLongDirective.directive_name = 'grrExtFlagsLinuxPickerLong';

exports.ExtFlagsLinuxPickerLongDirective = ExtFlagsLinuxPickerLongDirective;
