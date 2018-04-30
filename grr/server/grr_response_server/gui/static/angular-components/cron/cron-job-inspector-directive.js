'use strict';

goog.module('grrUi.cron.cronJobInspectorDirective');
goog.module.declareLegacyNamespace();



/**
 * CronJobInspectorDirective definition.
 *
 * @return {angular.Directive} Directive definition object.
 */
exports.CronJobInspectorDirective = function() {
  return {
    scope: {
      cronJobId: '=',
    },
    restrict: 'E',
    templateUrl: '/static/angular-components/cron/cron-job-inspector.html'
  };
};


/**
 * Directive's name in Angular.
 *
 * @const
 * @export
 */
exports.CronJobInspectorDirective.directive_name = 'grrCronJobInspector';
