goog.module('grrUi.acl.clientApprovalViewDirective');
goog.module.declareLegacyNamespace();

const routingService = goog.requireType('grrUi.routing.routingService');



/**
 * Controller for ClientApprovalViewDirective.
 * @unrestricted
 */
const ClientApprovalViewController = class {
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
    this.clientId;

    /** @type {string} */
    this.approvalId;

    this.grrRoutingService_.uiOnParamsChanged(
        this.scope_, ['username', 'clientId', 'approvalId'], function(params) {
          this.username = params[0];
          this.clientId = params[1];
          this.approvalId = params[2];
        }.bind(this));
  }
};


/**
 * ClientApprovalViewDirective definition.
 *
 * @return {angular.Directive} Directive definition object.
 */
exports.ClientApprovalViewDirective = function() {
  return {
    scope: {},
    restrict: 'E',
    templateUrl: '/static/angular-components/acl/client-approval-view.html',
    controller: ClientApprovalViewController,
    controllerAs: 'controller'
  };
};


/**
 * Name of the directive in Angular.
 *
 * @const
 * @export
 */
exports.ClientApprovalViewDirective.directive_name = 'grrClientApprovalView';
