goog.module('grrUi.cron.cronJobRunsListDirective');
goog.module.declareLegacyNamespace();



/**
 * Controller for cronJobRunsListDirective.
 *
 * @constructor
 * @param {!angular.Scope} $scope
 * @param {!grrUi.core.apiService.ApiService} grrApiService
 * @ngInject
 */
const CronJobRunsListController = function(
    $scope, grrApiService) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @private {!grrUi.core.apiService.ApiService} */
  this.grrApiService_ = grrApiService;

  /** @type {?string} */
  this.runsUrl;

  /** @type {?string} */
  this.cronJobId;

  /** @type {?Object} */
  this.selectedRun;

  this.scope_.$watch('cronJobId', this.onCronJobIdChange_.bind(this));
};


/**
 * Handles changes of clientId binding.
 *
 * @param {?string} cronJobId New binding value.
 * @private
 */
CronJobRunsListController.prototype.onCronJobIdChange_ = function(
    cronJobId) {
  if (angular.isString(cronJobId)) {
    var components = cronJobId.split('/');
    this.cronJobId  = components[components.length - 1];
    this.runsUrl = '/cron-jobs/' + this.cronJobId + '/runs';
  }
};

/**
 * Closes the run details div.
 */
CronJobRunsListController.prototype.closeDetails = function() {
  this.selectedRun = null;
};


/**
 * CronJobRunsListDirective definition.
 *
 * @return {angular.Directive} Directive definition object.
 */
exports.CronJobRunsListDirective = function() {
  return {
    scope: {
      cronJobId: '=',
      selectedRunId: '=?'
    },
    restrict: 'E',
    templateUrl: '/static/angular-components/cron/cron-job-runs-list.html',
    controller: CronJobRunsListController,
    controllerAs: 'controller'
  };
};


/**
 * Directive's name in Angular.
 *
 * @const
 * @export
 */
exports.CronJobRunsListDirective.directive_name = 'grrCronJobRunsList';
