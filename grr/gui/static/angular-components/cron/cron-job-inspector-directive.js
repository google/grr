'use strict';

goog.provide('grrUi.cron.cronJobInspectorDirective.CronJobInspectorDirective');

goog.scope(function() {

/**
 * CronJobInspectorDirective definition.
 *
 * @return {angular.Directive} Directive definition object.
 */
grrUi.cron.cronJobInspectorDirective.CronJobInspectorDirective = function() {
  return {
    scope: {
      cronJobUrn: '=',
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
grrUi.cron.cronJobInspectorDirective.CronJobInspectorDirective
    .directive_name = 'grrCronJobInspector';

});  // goog.scope
