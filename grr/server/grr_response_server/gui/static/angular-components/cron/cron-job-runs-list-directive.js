goog.module('grrUi.cron.cronJobRunsListDirective');
goog.module.declareLegacyNamespace();

const apiService = goog.requireType('grrUi.core.apiService');



/**
 * Controller for cronJobRunsListDirective.
 * @unrestricted
 */
const CronJobRunsListController = class {
  /**
   * @param {!angular.Scope} $scope
   * @param {!apiService.ApiService} grrApiService
   * @ngInject
   */
  constructor($scope, grrApiService) {
    /** @private {!angular.Scope} */
    this.scope_ = $scope;

    /** @private {!apiService.ApiService} */
    this.grrApiService_ = grrApiService;

    /** @type {?string} */
    this.runsUrl;

    /** @type {?string} */
    this.cronJobId;

    /** @type {?Object} */
    this.selectedRun;

    this.scope_.$watch('cronJobId', this.onCronJobIdChange_.bind(this));
  }

  /**
   * Handles changes of clientId binding.
   *
   * @param {?string} cronJobId New binding value.
   * @private
   */
  onCronJobIdChange_(cronJobId) {
    if (angular.isString(cronJobId)) {
      var components = cronJobId.split('/');
      this.cronJobId = components[components.length - 1];
      this.runsUrl = '/cron-jobs/' + this.cronJobId + '/runs';
    }
  }

  /**
   * Closes the run details div.
   */
  closeDetails() {
    this.selectedRun = null;
  }
};



/**
 * CronJobRunsListDirective definition.
 *
 * @return {angular.Directive} Directive definition object.
 */
exports.CronJobRunsListDirective = function() {
  return {
    scope: {cronJobId: '=', selectedRunId: '=?'},
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
