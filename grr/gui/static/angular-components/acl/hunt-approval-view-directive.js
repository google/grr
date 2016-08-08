'use strict';

goog.provide('grrUi.acl.huntApprovalViewDirective.HuntApprovalViewController');
goog.provide('grrUi.acl.huntApprovalViewDirective.HuntApprovalViewDirective');

goog.scope(function() {

/**
 * Controller for HuntApprovalViewDirective.
 *
 * @param {!angular.Scope} $scope
 * @param {!grrUi.routing.routingService.RoutingService} grrRoutingService
 * @constructor
 * @ngInject
 */
grrUi.acl.huntApprovalViewDirective.HuntApprovalViewController = function(
    $scope, grrRoutingService) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @private {!grrUi.routing.routingService.RoutingService} */
  this.grrRoutingService_ = grrRoutingService;

  /** @type {string} */
  this.username;

  /** @type {string} */
  this.huntId;

  /** @type {string} */
  this.approvalId;

  this.grrRoutingService_.uiOnParamsChanged(
      this.scope_, ['username', 'huntId', 'approvalId'],
      function(params) {
        this.username = params[0];
        this.huntId = params[1];
        this.approvalId = params[2];
      }.bind(this));
};
var HuntApprovalViewController =
    grrUi.acl.huntApprovalViewDirective.HuntApprovalViewController;


/**
 * HuntApprovalViewDirective definition.
 *
 * @return {angular.Directive} Directive definition object.
 */
grrUi.acl.huntApprovalViewDirective.HuntApprovalViewDirective = function() {
  return {
    scope: {},
    restrict: 'E',
    templateUrl: '/static/angular-components/acl/hunt-approval-view.html',
    controller: HuntApprovalViewController,
    controllerAs: 'controller'
  };
};


/**
 * Name of the directive in Angular.
 *
 * @const
 * @export
 */
grrUi.acl.huntApprovalViewDirective.HuntApprovalViewDirective.directive_name =
    'grrHuntApprovalView';

});  // goog.scope
