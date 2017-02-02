'use strict';

goog.provide('grrUi.client.clientContextDirective.ClientContextController');
goog.provide('grrUi.client.clientContextDirective.ClientContextDirective');

goog.scope(function() {


/**
 * Controller for ClientContextDirective.
 *
 * @constructor
 * @param {!angular.Scope} $scope
 * @ngInject
 */
grrUi.client.clientContextDirective.ClientContextController = function(
    $scope) {

  /** @type {?string} */
  this.clientId;

  $scope.$watch('clientId', this.onClientIdChange_.bind(this));
};

var ClientContextController =
    grrUi.client.clientContextDirective.ClientContextController;


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
grrUi.client.clientContextDirective.ClientContextDirective = function() {
  return {
    scope: {
      clientId: '='
    },
    restrict: 'E',
    transclude: true,
    template: '<ng-transclude></ng-transclude>',
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
grrUi.client.clientContextDirective.ClientContextDirective.directive_name =
    'grrClientContext';

});  // goog.scope
