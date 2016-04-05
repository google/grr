'use strict';

goog.provide('grrUi.cron.cronJobStatusIconDirective.CronJobStatusIconController');
goog.provide('grrUi.cron.cronJobStatusIconDirective.CronJobStatusIconDirective');


goog.scope(function() {


/**
 * Directive that displays cron status icons for a given cron.
 *
 * @constructor
 * @ngInject
 * @export
 */
grrUi.cron.cronJobStatusIconDirective.CronJobStatusIconDirective =
    function() {
      return {
        scope: {
          cronJob: '='
        },
        restrict: 'E',
        templateUrl: '/static/angular-components/cron/cron-job-status-icon.html'
      };
    };


/**
 * Name of the directive in Angular.
 */
grrUi.cron.cronJobStatusIconDirective.CronJobStatusIconDirective
    .directive_name = 'grrCronJobStatusIcon';


});  // goog.scope
