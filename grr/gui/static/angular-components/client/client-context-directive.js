'use strict';

goog.module('grrUi.client.clientContextDirective');
goog.module.declareLegacyNamespace();



/**
 * Controller for ClientContextDirective.
 *
 * @constructor
 * @param {!angular.Scope} $scope
 * @ngInject
 */
const ClientContextController = function(
    $scope) {

  /** @type {?string} */
  this.clientId;

  $scope.$watch('clientId', this.onClientIdChange_.bind(this));
};



/**
 * Handles clientId attribute changes.
 *
 * @param {?string} clientId
 * @private
 */
ClientContextController.prototype.onClientIdChange_ = function(clientId) {
  this.clientId = clientId;
};


/**
 * Directive for displaying the client context of a client with a given ID.
 *
 * @return {angular.Directive} Directive definition object.
 * @export
 */
exports.ClientContextDirective = function() {
  return {
    scope: {
      clientId: '='
    },
    restrict: 'E',
    transclude: true,
    template: '<ng-transclude ng-if="controller.clientId"></ng-transclude>',
    controller: ClientContextController,
    controllerAs: 'controller'
  };
};


/**
 * Directive's name in Angular.
 *
 * @const
 * @export
 */
exports.ClientContextDirective.directive_name = 'grrClientContext';
