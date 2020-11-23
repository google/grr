goog.module('grrUi.acl.huntFromFlowCopyReviewDirective');
goog.module.declareLegacyNamespace();

const routingService = goog.requireType('grrUi.routing.routingService');



/**
 * Controller for HuntFromFlowCopyReviewDirective.
 * @unrestricted
 */
const HuntFromFlowCopyReviewController = class {
  /**
   * @param {!angular.Scope} $scope
   * @param {!routingService.RoutingService} grrRoutingService
   * @ngInject
   */
  constructor($scope, grrRoutingService) {
    /** @private {!angular.Scope} */
    this.scope_ = $scope;

    /** @type {Object} */
    this.sourceFlow;

    /** @type {Object} */
    this.newFlow;

    this.scope_.$watchGroup(
        ['sourceFlow', 'newHunt'], this.onValuesChanged_.bind(this));
  }

  /**
   * @private
   */
  onValuesChanged_() {
    if (angular.isDefined(this.scope_['sourceFlow']) &&
        angular.isDefined(this.scope_['newHunt'])) {
      this.sourceFlow = this.scope_['sourceFlow'];

      this.newFlow = angular.copy(this.sourceFlow);
      var newHunt = this.scope_['newHunt'];
      this.newFlow['value']['name'] = newHunt['value']['flow_name'];
      this.newFlow['value']['args'] = newHunt['value']['flow_args'];
    }
  }
};



/**
 * HuntFromFlowCopyReviewDirective definition.
 *
 * @return {angular.Directive} Directive definition object.
 */
exports.HuntFromFlowCopyReviewDirective = function() {
  return {
    scope: {sourceFlow: '=', newHunt: '='},
    restrict: 'E',
    templateUrl:
        '/static/angular-components/acl/hunt-from-flow-copy-review.html',
    controller: HuntFromFlowCopyReviewController,
    controllerAs: 'controller'
  };
};


/**
 * Name of the directive in Angular.
 *
 * @const
 * @export
 */
exports.HuntFromFlowCopyReviewDirective.directive_name =
    'grrHuntFromFlowCopyReview';
