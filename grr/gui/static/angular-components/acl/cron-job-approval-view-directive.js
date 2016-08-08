'use strict';

goog.provide('grrUi.acl.cronJobApprovalViewDirective.CronJobApprovalViewController');
goog.provide('grrUi.acl.cronJobApprovalViewDirective.CronJobApprovalViewDirective');

goog.scope(function() {

/**
 * Controller for CronJobApprovalViewDirective.
 *
 * @param {!angular.Scope} $scope
 * @param {!grrUi.routing.routingService.RoutingService} grrRoutingService
 * @constructor
 * @ngInject
 */
grrUi.acl.cronJobApprovalViewDirective.CronJobApprovalViewController = function(
    $scope, grrRoutingService) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @private {!grrUi.routing.routingService.RoutingService} */
  this.grrRoutingService_ = grrRoutingService;

  /** @type {string} */
  this.username;

  /** @type {string} */
  this.cronJobId;

  /** @type {string} */
  this.approvalId;

  this.grrRoutingService_.uiOnParamsChanged(
      this.scope_, ['username', 'cronJobId', 'approvalId'],
      function(params) {
        this.username = params[0];
        this.cronJobId = params[1];
        this.approvalId = params[2];
      }.bind(this));
};
var CronJobApprovalViewController =
    grrUi.acl.cronJobApprovalViewDirective.CronJobApprovalViewController;


/**
 * CronJobApprovalViewDirective definition.
 *
 * @return {angular.Directive} Directive definition object.
 */
grrUi.acl.cronJobApprovalViewDirective.CronJobApprovalViewDirective = function() {
  return {
    scope: {},
    restrict: 'E',
    templateUrl: '/static/angular-components/acl/cron-job-approval-view.html',
    controller: CronJobApprovalViewController,
    controllerAs: 'controller'
  };
};


/**
 * Name of the directive in Angular.
 *
 * @const
 * @export
 */
grrUi.acl.cronJobApprovalViewDirective.CronJobApprovalViewDirective.directive_name =
    'grrCronJobApprovalView';

});  // goog.scope
