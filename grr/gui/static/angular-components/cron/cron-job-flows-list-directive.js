'use strict';

goog.provide('grrUi.cron.cronJobFlowsListDirective.CronJobFlowsListController');
goog.provide('grrUi.cron.cronJobFlowsListDirective.CronJobFlowsListDirective');

goog.scope(function() {

/**
 * Controller for cronJobFlowsListDirective.
 *
 * @constructor
 * @param {!angular.Scope} $scope
 * @param {!grrUi.core.apiService.ApiService} grrApiService
 * @ngInject
 */
grrUi.cron.cronJobFlowsListDirective.CronJobFlowsListController = function(
    $scope, grrApiService) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @private {!grrUi.core.apiService.ApiService} */
  this.grrApiService_ = grrApiService;

  /** @type {?string} */
  this.flowsUrl;

  /** @type {?string} */
  this.cronJobId;

  /** @type {?string} */
  this.selectedFlowId;

  this.scope_.$watch('cronJobUrn', this.onCronJobUrnChange_.bind(this));
};
var CronJobFlowsListController =
    grrUi.cron.cronJobFlowsListDirective.CronJobFlowsListController;


/**
 * Handles changes of clientId binding.
 *
 * @param {?string} cronJobUrn New binding value.
 * @private
 */
CronJobFlowsListController.prototype.onCronJobUrnChange_ = function(
    cronJobUrn) {
  if (angular.isString(cronJobUrn)) {
    var components = cronJobUrn.split('/');
    this.cronJobId  = components[components.length - 1];
    this.flowsUrl = '/cron-jobs/' + this.cronJobId + '/flows';
  }
};


/**
 * Closes the flow details div.
 */
CronJobFlowsListController.prototype.closeDetails = function() {
  this.selectedFlowId = null;
};


/**
 * CronJobFlowsListDirective definition.
 *
 * @return {angular.Directive} Directive definition object.
 */
grrUi.cron.cronJobFlowsListDirective.CronJobFlowsListDirective = function() {
  return {
    scope: {
      cronJobUrn: '=',
      selectedFlowUrn: '=?'
    },
    restrict: 'E',
    templateUrl: '/static/angular-components/cron/cron-job-flows-list.html',
    controller: CronJobFlowsListController,
    controllerAs: 'controller'
  };
};


/**
 * Directive's name in Angular.
 *
 * @const
 * @export
 */
grrUi.cron.cronJobFlowsListDirective.CronJobFlowsListDirective
    .directive_name = 'grrCronJobFlowsList';

});  // goog.scope
