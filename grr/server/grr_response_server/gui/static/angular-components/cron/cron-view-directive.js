goog.module('grrUi.cron.cronViewDirective');
goog.module.declareLegacyNamespace();

const routingService = goog.requireType('grrUi.routing.routingService');



/**
 * Controller for CronViewDirective.
 * @unrestricted
 */
const CronViewController = class {
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
    this.selectedCronJobId;

    this.scope_.$watch(
        'controller.selectedCronJobId',
        this.onSelectedCronJobIdChange_.bind(this));
    this.grrRoutingService_.uiOnParamsChanged(
        this.scope_, 'cronJobId', this.onParamsChange_.bind(this));
  }

  /**
   * Handles changes to the state params.
   *
   * @param {string} cronJobId The new value for the selected cron job.
   * @private
   */
  onParamsChange_(cronJobId) {
    if (cronJobId) {
      this.selectedCronJobId = cronJobId;
    }
  }

  /**
   * Handles selectedCronJobId binding changes.
   *
   * @param {?string} newValue New binding value.
   * @private
   */
  onSelectedCronJobIdChange_(newValue) {
    if (angular.isDefined(newValue)) {
      this.grrRoutingService_.go('crons', {cronJobId: newValue});
    }
  }
};



/**
 * CronsViewDirective definition.

 * @return {angular.Directive} Directive definition object.
 */
exports.CronViewDirective = function() {
  return {
    scope: {},
    restrict: 'E',
    templateUrl: '/static/angular-components/cron/cron-view.html',
    controller: CronViewController,
    controllerAs: 'controller'
  };
};


/**
 * Directive's name in Angular.
 *
 * @const
 * @export
 */
exports.CronViewDirective.directive_name = 'grrCronView';
