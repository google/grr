'use strict';

goog.module('grrUi.semantic.rekall.rekallValueDirective');
goog.module.declareLegacyNamespace();

const {camelCaseToDashDelimited} = goog.require('grrUi.core.utils');



/**
 * Controller for RekallValueDirective.
 *
 * @param {!angular.Scope} $scope
 * @param {!jQuery} $element
 * @param {!angular.$compile} $compile
 * @param {!grrUi.semantic.rekall.rekallRegistryService.RekallRegistryService}
 *     grrRekallDirectivesRegistryService
 * @constructor
 * @ngInject
 */
const RekallValueController = function(
    $scope, $element, $compile, grrRekallDirectivesRegistryService) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @private {!jQuery} */
  this.element_ = $element;

  /** @private {!angular.$compile} */
  this.compile_ = $compile;

  /**
   * @private {!grrUi.semantic.rekall.rekallRegistryService.RekallRegistryService}
   */
  this.grrRekallDirectivesRegistryService_ = grrRekallDirectivesRegistryService;

  this.scope_.$watch('::value', this.onValueChange_.bind(this));
};



/**
 * @param {?} value
 * @private
 */
RekallValueController.prototype.onValueChange_ = function(value) {
  if (value === null || angular.isUndefined(value)) {
    return;
  }

  if (!angular.isObject(value)) {
    this.element_.text(value.toString());
    return;
  }

  var directive = this.grrRekallDirectivesRegistryService_.findDirectiveForMro(
      value['mro']);

  /** @type {string} */
  var tag = 'grr-rekall-default-value';

  if (angular.isDefined(directive)) {
    tag = camelCaseToDashDelimited(directive.directive_name);
  }

  this.element_.html('<' + tag + ' value="::value"></' + tag + '>');
  this.compile_(this.element_.contents())(this.scope_);
};


/**
 * Directive that displays Rekall objects recursively in tables.
 *
 * @return {!angular.Directive} Directive definition object.
 * @ngInject
 * @export
 */
exports.RekallValueDirective = function() {
  return {
    scope: {
      value: '='
    },
    restrict: 'E',
    controller: RekallValueController,
    controllerAs: 'controller'
  };
};


/**
 * Name of the directive in Angular.
 *
 * @const
 * @export
 */
exports.RekallValueDirective.directive_name = 'grrRekallValue';
