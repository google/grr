goog.module('grrUi.acl.cronJobApprovalViewDirective');
goog.module.declareLegacyNamespace();

const routingService = goog.requireType('grrUi.routing.routingService');



/**
 * Controller for CronJobApprovalViewDirective.
 * @unrestricted
 */
const CronJobApprovalViewController = class {
  /**
   * @param {!angular.Scope} $scope
   * @param {!routingService.RoutingService} grrRoutingService
   * @ngInject
   */
  constructor($scope, grrRoutingService) {
    /** @private {!angular.Scope} */
    this.scope_ = $scope;

    /** @private {!routingService.RoutingService} */
    this.grrRoutingService_ = grrRoutingService;

    /** @type {string} */
    this.username;

    /** @type {string} */
    this.cronJobId;

    /** @type {string} */
    this.approvalId;

    this.grrRoutingService_.uiOnParamsChanged(
        this.scope_, ['username', 'cronJobId', 'approvalId'], function(params) {
          this.username = params[0];
          this.cronJobId = params[1];
          this.approvalId = params[2];
        }.bind(this));
  }
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
