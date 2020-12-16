goog.module('grrUi.hunt.huntsViewDirective');
goog.module.declareLegacyNamespace();

const routingService = goog.requireType('grrUi.routing.routingService');



/**
 * Controller for HuntsViewDirective.
 * @unrestricted
 */
const HuntsViewController = class {
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
    this.selectedHuntId;

    /** @type {string} */
    this.tab;

    this.scope_.$watchGroup(
        ['controller.selectedHuntId', 'controller.tab'],
        this.onSelectionChange_.bind(this));

    this.grrRoutingService_.uiOnParamsChanged(
        this.scope_, ['huntId', 'tab'], this.onParamsChange_.bind(this));
  }

  /**
   * Handles changes to the state params.
   *
   * @param {Array} newValues The new values for the watched params.
   * @param {Object=} opt_stateParams A dictionary of all state params and their
   *     values.
   * @private
   */
  onParamsChange_(newValues, opt_stateParams) {
    if (opt_stateParams['huntId']) {
      this.selectedHuntId = opt_stateParams['huntId'];
    }
    this.tab = opt_stateParams['tab'];
  }

  /**
   * Handles changes to the selected hunt or tab.
   *
   * @private
   */
  onSelectionChange_() {
    if (angular.isDefined(this.selectedHuntId)) {
      this.grrRoutingService_.go(
          'hunts', {huntId: this.selectedHuntId, tab: this.tab});
    }
  }
};



/**
 * HuntsViewDirective definition.
 * @return {angular.Directive} Directive definition object.
 */
exports.HuntsViewDirective = function() {
  return {
    restrict: 'E',
    scope: {},
    templateUrl: '/static/angular-components/hunt/hunts-view.html',
    controller: HuntsViewController,
    controllerAs: 'controller'
  };
};


/**
 * Name of the directive in Angular.
 *
 * @const
 * @export
 */
exports.HuntsViewDirective.directive_name = 'grrHuntsView';
