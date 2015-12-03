'use strict';

goog.provide('grrUi.outputPlugins.csvOutputPluginDirective.CsvOutputPluginController');
goog.provide('grrUi.outputPlugins.csvOutputPluginDirective.CsvOutputPluginDirective');


goog.scope(function() {


/**
 * Controller for CsvOutputPluginDirective.
 *
 * @constructor
 * @param {!angular.Scope} $scope
 * @ngInject
 */
grrUi.outputPlugins.csvOutputPluginDirective.CsvOutputPluginController =
    function($scope) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @export {boolean} */
  this.hasStreams = false;

  this.scope_.$watch(
      'outputPlugin.value.state.value.output_streams.value',
      function(newValue) {
        this.hasStreams = angular.isDefined(newValue) &&
            Object.keys(newValue).length > 0;
      }.bind(this));
};
var CsvOutputPluginController =
    grrUi.outputPlugins.csvOutputPluginDirective.CsvOutputPluginController;


/**
 * Directive for displaying output plugin note for CSV plugin.
 *
 * @constructor
 * @ngInject
 * @export
 */
grrUi.outputPlugins.csvOutputPluginDirective.CsvOutputPluginDirective =
    function() {
  return {
    scope: {
      outputPlugin: '='
    },
    restrict: 'E',
    templateUrl: '/static/angular-components/output-plugins/' +
        'csv-output-plugin.html',
    controller: CsvOutputPluginController,
    controllerAs: 'controller'
  };
};


/**
 * Output plugin type this directive handles.
 *
 * @const
 * @export
 */
grrUi.outputPlugins.csvOutputPluginDirective.CsvOutputPluginDirective
    .output_plugin_type = 'CSVOutputPlugin';


/**
 * Output plugin type this directive handles.
 *
 * @const
 * @export
 */
grrUi.outputPlugins.csvOutputPluginDirective.CsvOutputPluginDirective
    .output_plugin_title = 'CSV Output';


/**
 * Directive's name in Angular.
 *
 * @const
 * @export
 */
grrUi.outputPlugins.csvOutputPluginDirective.CsvOutputPluginDirective
    .directive_name = 'grrCsvOutputPlugin';


});  // goog.scope
