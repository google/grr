'use strict';

goog.provide('grrUi.semantic.rekall.rekallValueDirective.RekallValueController');
goog.provide('grrUi.semantic.rekall.rekallValueDirective.RekallValueDirective');

goog.require('grrUi.core.utils.camelCaseToDashDelimited');

goog.scope(function() {

/**
 * Controller for RekallValueDirective.
 *
 * @param {!angular.Scope} $scope
 * @param {!jQuery} $element
 * @param {!angular.$compile} $compile
 * @param {!grrUi.semantic.rekall.rekallRegistry.RekallRegistryService}
 *     grrRekallDirectivesRegistryService
 * @constructor
 * @ngInject
 */
grrUi.semantic.rekall.rekallValueDirective.RekallValueController = function(
    $scope, $element, $compile, grrRekallDirectivesRegistryService) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @private {!jQuery} */
  this.element_ = $element;

  /** @private {!angular.$compile} */
  this.compile_ = $compile;

  /** @private {!grrUi.semantic.rekall.rekallRegistry.RekallRegistryService} */
  this.grrRekallDirectivesRegistryService_ = grrRekallDirectivesRegistryService;

  this.scope_.$watch('::value', this.onValueChange_.bind(this));
};

var RekallValueController =
    grrUi.semantic.rekall.rekallValueDirective.RekallValueController;


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
    tag = grrUi.core.utils.camelCaseToDashDelimited(directive.directive_name);
  }

  this.element_.html('<' + tag + ' value="::value"></' + tag + '>');
  this.compile_(this.element_.contents())(this.scope_);
};


/**
 * Directive that displays Rekall objects recursively in tables.
 *
 * @return {!angular.Directive} Directive definition object.
 * @constructor
 * @ngInject
 * @export
 */
grrUi.semantic.rekall.rekallValueDirective.RekallValueDirective = function() {
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
grrUi.semantic.rekall.rekallValueDirective.RekallValueDirective.directive_name =
    'grrRekallValue';

});  // goog.scope
