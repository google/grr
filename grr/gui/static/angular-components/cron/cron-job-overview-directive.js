'use strict';

goog.provide('grrUi.cron.cronJobOverviewDirective');
goog.provide('grrUi.cron.cronJobOverviewDirective.CronJobOverviewDirective');
goog.require('grrUi.core.utils');  // USE: stripAff4Prefix

goog.scope(function() {


var stripAff4Prefix = grrUi.core.utils.stripAff4Prefix;


/**
 * Controller for CronJobOverviewDirective.
 *
 * @constructor
 * @param {!angular.Scope} $scope
 * @param {!grrUi.core.apiService.ApiService} grrApiService
 * @ngInject
 */
const CronJobOverviewController =
    function($scope, grrApiService) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @type {string} */
  this.scope_.cronJobId;

  /** @private {!grrUi.core.apiService.ApiService} */
  this.grrApiService_ = grrApiService;

  /** @export {Object} */
  this.cronJob;

  /** @export {string} */
  this.cronJobId;

  this.scope_.$watch('cronJobId', this.onCronJobIdChange.bind(this));
};



/**
 * Handles cronJobId attribute changes.
 *
 * @param {string} newCronJobId
 * @export
 */
CronJobOverviewController.prototype.onCronJobIdChange = function(
    newCronJobId) {
  this.cronJob = null;

  if (angular.isDefined(newCronJobId)) {
    this.cronJobId = newCronJobId;
    this.grrApiService_.get('cron-jobs/' + this.cronJobId)
        .then(this.onCronJobFetched.bind(this));
  }
};


/**
 * Called when cronJob data was fetched.
 * @param {Object} response Response from the server.
 */
CronJobOverviewController.prototype.onCronJobFetched = function(response) {
  this.cronJob = response.data;
};


/**
 * Directive for displaying log records of a cronJob with a given id
 *
 * @return {angular.Directive} Directive definition object.
 * @ngInject
 * @export
 */
grrUi.cron.cronJobOverviewDirective.CronJobOverviewDirective = function() {
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
grrUi.cron.cronJobOverviewDirective.CronJobOverviewDirective.directive_name =
    'grrCronJobOverview';

});  // goog.scope
