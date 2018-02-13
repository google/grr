'use strict';

goog.module('grrUi.cron.cronJobStatusIconDirective');
goog.module.declareLegacyNamespace();



/**
 * Directive that displays cron status icons for a given cron.
 *
 * @return {!angular.Directive} Directive definition object.
 * @ngInject
 * @export
 */
exports.CronJobStatusIconDirective = function() {
  return {
    scope: {cronJob: '='},
    restrict: 'E',
    templateUrl: '/static/angular-components/cron/cron-job-status-icon.html'
  };
};


/**
 * Name of the directive in Angular.
 */
exports.CronJobStatusIconDirective.directive_name = 'grrCronJobStatusIcon';
