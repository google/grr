'use strict';

goog.provide('grrUi.cron.cronViewDirective.CronViewController');
goog.provide('grrUi.cron.cronViewDirective.CronViewDirective');

goog.scope(function() {


/**
 * Controller for CronViewDirective.
 *
 * @constructor
 * @param {!angular.Scope} $scope
 * @param {!grrUi.routing.routingService.RoutingService} grrRoutingService
 * @ngInject
 */
grrUi.cron.cronViewDirective.CronViewController = function(
    $scope, grrRoutingService) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @private {!grrUi.routing.routingService.RoutingService} */
  this.grrRoutingService_ = grrRoutingService;

  /** @type {string} */
  this.selectedCronJobUrn;

  this.scope_.$watch('controller.selectedCronJobUrn',
                     this.onSelectedCronJobUrnChange_.bind(this));
  this.grrRoutingService_.uiOnParamsChanged(this.scope_, 'cronJobId',
      this.onParamsChange_.bind(this));
};
var CronViewController =
    grrUi.cron.cronViewDirective.CronViewController;


/**
 * Handles changes to the state params.
 *
 * @param {Array} cronJobId The new value for the selected cron job.
 * @private
 */
CronViewController.prototype.onParamsChange_ = function(cronJobId) {
  if (cronJobId) {
    this.selectedCronJobUrn = 'aff4:/cron/' + cronJobId;
  }
};

/**
 * Handles selectedCronUrn binding changes.
 *
 * @param {?string} newValue New binding value.
 * @private
 */
CronViewController.prototype.onSelectedCronJobUrnChange_ = function(
    newValue) {
  if (angular.isDefined(newValue)) {
    var cronJobId = this.selectedCronJobUrn.split('/')[2];
    this.grrRoutingService_.go('crons', {cronJobId: cronJobId});
  }
};


/**
 * CronsViewDirective definition.

 * @return {angular.Directive} Directive definition object.
 */
grrUi.cron.cronViewDirective.CronViewDirective = function() {
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
grrUi.cron.cronViewDirective.CronViewDirective
    .directive_name = 'grrCronView';



});  // goog.scope
