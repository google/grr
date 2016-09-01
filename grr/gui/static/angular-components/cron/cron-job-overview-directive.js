'use strict';

goog.provide('grrUi.cron.cronJobOverviewDirective.CronJobOverviewController');
goog.provide('grrUi.cron.cronJobOverviewDirective.CronJobOverviewDirective');
goog.require('grrUi.core.utils.stripAff4Prefix');

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
grrUi.cron.cronJobOverviewDirective.CronJobOverviewController =
    function($scope, grrApiService) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @type {string} */
  this.scope_.cronJobUrn;

  /** @private {!grrUi.core.apiService.ApiService} */
  this.grrApiService_ = grrApiService;

  /** @export {Object} */
  this.cronJob;

  /** @export {string} */
  this.cronJobId;

  this.scope_.$watch('cronJobUrn', this.onCronJobUrnChange.bind(this));
};

var CronJobOverviewController =
    grrUi.cron.cronJobOverviewDirective.CronJobOverviewController;


/**
 * Handles cronJobUrn attribute changes.
 *
 * @param {string} newCronJobUrn
 * @export
 */
CronJobOverviewController.prototype.onCronJobUrnChange = function(
    newCronJobUrn) {
  this.cronJob = null;

  if (angular.isDefined(newCronJobUrn)) {
    var cronJobUrnComponents = stripAff4Prefix(newCronJobUrn).split('/');
    this.cronJobId = cronJobUrnComponents[cronJobUrnComponents.length - 1];

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
 * Directive for displaying log records of a cronJob with a given URN.
 *
 * @return {angular.Directive} Directive definition object.
 * @ngInject
 * @export
 */
grrUi.cron.cronJobOverviewDirective.CronJobOverviewDirective = function() {
  return {
    scope: {
      cronJobUrn: '=',
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
