'use strict';

goog.module('grrUi.cron.cronJobFlowsListDirective');
goog.module.declareLegacyNamespace();



/**
 * Controller for cronJobFlowsListDirective.
 *
 * @constructor
 * @param {!angular.Scope} $scope
 * @param {!grrUi.core.apiService.ApiService} grrApiService
 * @ngInject
 */
const CronJobFlowsListController = function(
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

  this.scope_.$watch('cronJobId', this.onCronJobIdChange_.bind(this));
};


/**
 * Handles changes of clientId binding.
 *
 * @param {?string} cronJobId New binding value.
 * @private
 */
CronJobFlowsListController.prototype.onCronJobIdChange_ = function(
    cronJobId) {
  if (angular.isString(cronJobId)) {
    var components = cronJobId.split('/');
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
exports.CronJobFlowsListDirective = function() {
  return {
    scope: {
      cronJobId: '=',
      selectedFlowId: '=?'
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
exports.CronJobFlowsListDirective.directive_name = 'grrCronJobFlowsList';
