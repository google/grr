'use strict';

goog.module('grrUi.acl.cronJobApprovalViewDirective');
goog.module.declareLegacyNamespace();



/**
 * Controller for CronJobApprovalViewDirective.
 *
 * @param {!angular.Scope} $scope
 * @param {!grrUi.routing.routingService.RoutingService} grrRoutingService
 * @constructor
 * @ngInject
 */
const CronJobApprovalViewController = function(
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


/**
 * CronJobApprovalViewDirective definition.
 *
 * @return {angular.Directive} Directive definition object.
 */
exports.CronJobApprovalViewDirective = function() {
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
exports.CronJobApprovalViewDirective.directive_name = 'grrCronJobApprovalView';
