'use strict';

goog.module('grrUi.semantic.urnDirective');
goog.module.declareLegacyNamespace();

const {aff4UrnToUrl} = goog.require('grrUi.routing.aff4UrnToUrl');



/**
 * Controller for UrnDirective.
 *
 * @param {!angular.Scope} $scope
 * @param {!grrUi.routing.routingService.RoutingService} grrRoutingService
 * @constructor
 * @ngInject
 */
const UrnController = function(
    $scope, grrRoutingService) {

  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @private {!grrUi.routing.routingService.RoutingService} */
  this.grrRoutingService_ = grrRoutingService;

  /** @type {string} */
  this.plainValue;

  /** @type {string} */
  this.ref;

  /** @type {string} */
  this.refState;

  /** @type {Object} */
  this.refParams;

  this.scope_.$watch('::value', this.onValueChange_.bind(this));
};


/**
 * Handles value changes.
 *
 * @param {string} newValue
 * @private
 */
UrnController.prototype.onValueChange_ = function(newValue) {
  if (angular.isObject(newValue)) {
    this.plainValue = newValue.value;
  } else if (angular.isString(newValue)) {
    this.plainValue = newValue;
  } else {
    return;
  }

  var urlResult = aff4UrnToUrl(this.plainValue);
  if (urlResult) {
    this.refState = urlResult.state;
    this.refParams = urlResult.params;

    this.ref = this.grrRoutingService_.href(urlResult.state, urlResult.params);
  }
};


/**
 * Handles clicks on the link.
 * @export
 */
UrnController.prototype.onClick = function() {
  this.grrRoutingService_.go('client.vfs', this.refParams);
};


/**
 * Directive that displays RDFURN values.
 *
 * @return {!angular.Directive} Directive definition object.
 * @ngInject
 * @export
 */
exports.UrnDirective = function() {
  return {
    scope: {
      value: '='
    },
    restrict: 'E',
    templateUrl: '/static/angular-components/semantic/urn.html',
    controller: UrnController,
    controllerAs: 'controller'
  };
};


/**
 * Directive's name in Angular.
 *
 * @const
 * @export
 */
exports.UrnDirective.directive_name = 'grrUrn';

/**
 * Semantic type corresponding to this directive.
 *
 * @const
 * @export
 */
exports.UrnDirective.semantic_type = 'RDFURN';
