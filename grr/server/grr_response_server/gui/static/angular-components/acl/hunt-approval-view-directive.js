goog.module('grrUi.acl.huntApprovalViewDirective');
goog.module.declareLegacyNamespace();

const routingService = goog.requireType('grrUi.routing.routingService');



/**
 * Controller for HuntApprovalViewDirective.
 * @unrestricted
 */
const HuntApprovalViewController = class {
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
    this.huntId;

    /** @type {string} */
    this.approvalId;

    /** @type {Object} */
    this.approvalObject;

    this.grrRoutingService_.uiOnParamsChanged(
        this.scope_, ['username', 'huntId', 'approvalId'], function(params) {
          this.username = params[0];
          this.huntId = params[1];
          this.approvalId = params[2];
        }.bind(this));
  }
};


/**
 * HuntApprovalViewDirective definition.
 *
 * @return {angular.Directive} Directive definition object.
 */
exports.HuntApprovalViewDirective = function() {
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
exports.HuntApprovalViewDirective.directive_name = 'grrHuntApprovalView';
