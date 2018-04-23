'use strict';

goog.module('grrUi.forms.extFlagsOsxPickerDirective');
goog.module.declareLegacyNamespace();

const {OSX_FLAGS} = goog.require('grrUi.client.extFlags');
const {TroggableFlags} = goog.require('grrUi.forms.extFlagsTroggling');


/**
 * @constructor
 * @param {!angular.Scope} $scope
 * @ngInject
 */
const ExtFlagsOsxPickerController = function($scope) {
  /** @type {!TroggableFlags} */
  this.flags = new TroggableFlags(OSX_FLAGS);

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
 *
 * @return {!angular.Directive} Directive definition object.
 */
const ExtFlagsOsxPickerDirective = function() {
  return {
    restrict: 'E',
    scope: {
      bitsSet: '=',
      bitsUnset: '=',
    },
    templateUrl: '/static/angular-components/forms/ext-flags-osx-picker.html',
    controller: ExtFlagsOsxPickerController,
    controllerAs: 'controller',
  };
};

/**
 * Name of the directive in Angular.
 *
 * @const
 * @export
 */
ExtFlagsOsxPickerDirective.directive_name = 'grrExtFlagsOsxPicker';

exports.ExtFlagsOsxPickerDirective = ExtFlagsOsxPickerDirective;
