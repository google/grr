'use strict';

goog.provide('grrUi.cron.cronViewDirective.CronViewController');
goog.provide('grrUi.cron.cronViewDirective.CronViewDirective');

goog.scope(function() {


/**
 * Controller for CronViewDirective.
 *
 * @constructor
 * @param {!angular.Scope} $scope
 * @ngInject
 */
grrUi.cron.cronViewDirective.CronViewController = function(
    $scope) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @type {string} */
  this.selectedCronJobUrn;

  // TODO(user): use Angular service for this.
  if (angular.isDefined(grr.hash['cron_job_urn'])) {
    this.selectedCronJobUrn = grr.hash['cron_job_urn'];
  }

  this.scope_.$watch('controller.selectedCronJobUrn',
                     this.onSelectedCronJobUrnChange_.bind(this));

};
var CronViewController =
    grrUi.cron.cronViewDirective.CronViewController;


/**
 * Handles selectedCronUrn binding changes.
 *
 * @param {?string} newValue New binding value.
 * @private
 */
CronViewController.prototype.onSelectedCronJobUrnChange_ = function(
    newValue) {
  if (angular.isDefined(newValue)) {
    // TODO(user): use Angular service for this.
    grr.publish('hash_state', 'cron_job_urn', this.selectedCronJobUrn);
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
