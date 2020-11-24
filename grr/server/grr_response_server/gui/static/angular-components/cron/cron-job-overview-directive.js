goog.module('grrUi.cron.cronJobOverviewDirective');
goog.module.declareLegacyNamespace();

const apiService = goog.requireType('grrUi.core.apiService');


/**
 * Controller for CronJobOverviewDirective.
 * @unrestricted
 */
const CronJobOverviewController = class {
  /**
   * @param {!angular.Scope} $scope
   * @param {!apiService.ApiService} grrApiService
   * @ngInject
   */
  constructor($scope, grrApiService) {
    /** @private {!angular.Scope} */
    this.scope_ = $scope;

    /** @type {string} */
    this.scope_.cronJobId;

    /** @private {!apiService.ApiService} */
    this.grrApiService_ = grrApiService;

    /** @export {Object} */
    this.cronJob;

    /** @export {string} */
    this.cronJobId;

    this.scope_.$watch('cronJobId', this.onCronJobIdChange.bind(this));
  }

  /**
   * Handles cronJobId attribute changes.
   *
   * @param {string} newCronJobId
   * @export
   */
  onCronJobIdChange(newCronJobId) {
    this.cronJob = null;

    if (angular.isDefined(newCronJobId)) {
      this.cronJobId = newCronJobId;
      this.grrApiService_.get('cron-jobs/' + this.cronJobId)
          .then(this.onCronJobFetched.bind(this));
    }
  }

  /**
   * Called when cronJob data was fetched.
   * @param {Object} response Response from the server.
   */
  onCronJobFetched(response) {
    this.cronJob = response.data;
  }
};



/**
 * Directive for displaying log records of a cronJob with a given id
 *
 * @return {angular.Directive} Directive definition object.
 * @ngInject
 * @export
 */
exports.CronJobOverviewDirective = function() {
  return {
    scope: {
      cronJobId: '=',
    },
    restrict: 'E',
    templateUrl: '/static/angular-components/cron/cron-job-overview.html',
    controller: CronJobOverviewController,
    controllerAs: 'controller'
  };
};


/**
 * Directive's name in Angular.
 *
 * @const
 * @export
 */
exports.CronJobOverviewDirective.directive_name = 'grrCronJobOverview';
