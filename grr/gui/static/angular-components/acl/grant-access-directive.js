'use strict';

goog.provide('grrUi.acl.grantAccessDirective.GrantAccessController');
goog.provide('grrUi.acl.grantAccessDirective.GrantAccessDirective');

goog.scope(function() {

/**
 * Controller for GrantAccessDirective.
 *
 * @param {!angular.Scope} $scope
 * @param {!grrUi.routing.routingService.RoutingService} grrRoutingService
 * @constructor
 * @ngInject
 */
grrUi.acl.grantAccessDirective.GrantAccessController = function(
    $scope, grrRoutingService) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @private {!grrUi.routing.routingService.RoutingService} */
  this.grrRoutingService_ = grrRoutingService;

  /** @type {string} */
  this.aclItem;

  this.grrRoutingService_.uiOnParamsChanged(this.scope_, 'acl',
      this.onAclChange_.bind(this));
};
var GrantAccessController =
    grrUi.acl.grantAccessDirective.GrantAccessController;


/**
 * Handles changes to the acl state param.
 *
 * @param {string} aclItem The new acl item.
 * @private
 */
GrantAccessController.prototype.onAclChange_ = function(aclItem) {
  this.aclItem = aclItem;
};

/**
 * GrantAccessDirective definition.
 *
 * @return {angular.Directive} Directive definition object.
 */
grrUi.acl.grantAccessDirective.GrantAccessDirective = function() {
  return {
    scope: {},
    restrict: 'E',
    templateUrl: '/static/angular-components/acl/grant-access.html',
    controller: GrantAccessController,
    controllerAs: 'controller'
  };
};


/**
 * Name of the directive in Angular.
 *
 * @const
 * @export
 */
grrUi.acl.grantAccessDirective.GrantAccessDirective.directive_name =
    'grrGrantAccess';

});  // goog.scope
