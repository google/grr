'use strict';

goog.provide('grrUi.hunt.huntDetailsDirective.HuntDetailsController');
goog.provide('grrUi.hunt.huntDetailsDirective.HuntDetailsDirective');

goog.scope(function() {

/**
 * Controller for HuntDetailsDirective.
 *
 * @param {!angular.Scope} $scope
 * @param {!grrUi.routing.routingService.RoutingService} grrRoutingService
 * @constructor
 * @ngInject
 */
grrUi.hunt.huntDetailsDirective.HuntDetailsController = function(
    $scope, grrRoutingService) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @private {!grrUi.routing.routingService.RoutingService} */
  this.grrRoutingService_ = grrRoutingService;

  /** @type {string} */
  this.huntUrn;

  this.grrRoutingService_.uiOnParamsChanged(this.scope_, 'huntId',
      this.onHuntIdChange_.bind(this));
};
var HuntDetailsController =
    grrUi.hunt.huntDetailsDirective.HuntDetailsController;


/**
 * Handles changes to the hunt id state param.
 *
 * @param {string} huntId The new hunt id.
 * @private
 */
HuntDetailsController.prototype.onHuntIdChange_ = function(huntId) {
  if (huntId) {
    this.huntUrn = 'aff4:/hunts/' + huntId;
  }
};

/**
 * HuntDetailsDirective definition.
 *
 * @return {angular.Directive} Directive definition object.
 */
grrUi.hunt.huntDetailsDirective.HuntDetailsDirective = function() {
  return {
    scope: {},
    restrict: 'E',
    templateUrl: '/static/angular-components/hunt/hunt-details.html',
    controller: HuntDetailsController,
    controllerAs: 'controller'
  };
};


/**
 * Name of the directive in Angular.
 *
 * @const
 * @export
 */
grrUi.hunt.huntDetailsDirective.HuntDetailsDirective.directive_name =
    'grrHuntDetails';

});  // goog.scope
