'use strict';

goog.provide('grrUi.outputPlugins.outputPluginNoteDirective.OutputPluginNoteController');
goog.provide('grrUi.outputPlugins.outputPluginNoteDirective.OutputPluginNoteDirective');


goog.scope(function() {

/**
 * Controller for OutputPluginNoteDirective.
 *
 * @constructor
 * @param {!angular.Scope} $scope
 * @param {!grrUi.core.semanticRegistry.SemanticRegistryService}
 *     grrOutputPluginsDirectivesRegistryService
 * @ngInject
 */
grrUi.outputPlugins.outputPluginNoteDirective.OutputPluginNoteController =
    function($scope, grrOutputPluginsDirectivesRegistryService) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @type {Object} */
  this.scope_.outputPlugin;

  /** @type {string} */
  this.pluginTitle;

  /** @type {string} */
  this.pluginLogsUrl;

  /** @type {string} */
  this.pluginErrorsUrl;

  /** @private {!grrUi.core.semanticRegistry.SemanticRegistryService} */
  this.grrOutputPluginsDirectivesRegistryService_ =
      grrOutputPluginsDirectivesRegistryService;

  this.scope_.$watchGroup(['outputPlugin', 'outputPluginsUrl'],
                          this.onOutputPluginChange_.bind(this));
};
var OutputPluginNoteController =
    grrUi.outputPlugins.outputPluginNoteDirective.OutputPluginNoteController;


/**
 * Handles changes in descriptor or state.
 *
 * @private
 */
OutputPluginNoteController.prototype.onOutputPluginChange_ = function() {
  if (angular.isDefined(this.scope_['outputPlugin']) &&
      angular.isDefined(this.scope_['outputPluginsUrl'])) {
    var descriptor =
        this.scope_['outputPlugin']['value']['plugin_descriptor'];
    var pluginName = descriptor['value']['plugin_name']['value'];

    var directive = this.grrOutputPluginsDirectivesRegistryService_
        .findDirectiveForMro([pluginName]);
    if (angular.isDefined(directive)) {
      this.pluginTitle = directive.output_plugin_title;
    } else {
      this.pluginTitle = pluginName;
    }

    var logsUrlBase = this.scope_['outputPluginsUrl'] + '/' +
        this.scope_['outputPlugin']['value']['id']['value'];
    this.pluginLogsUrl = logsUrlBase + '/logs';
    this.pluginErrorsUrl = logsUrlBase + '/errors';
  }
};

/**
 * Directive for displaying notes for output plugins of a flow or hunt.
 *
 * @constructor
 * @ngInject
 * @export
 */
grrUi.outputPlugins.outputPluginNoteDirective.OutputPluginNoteDirective =
    function() {
  return {
    scope: {
      outputPluginsUrl: '=',
      outputPlugin: '='
    },
    restrict: 'E',
    templateUrl: '/static/angular-components/output-plugins/' +
        'output-plugin-note.html',
    controller: OutputPluginNoteController,
    controllerAs: 'controller'
  };
};

/**
 * Directive's name in Angular.
 *
 * @const
 * @export
 */
grrUi.outputPlugins.outputPluginNoteDirective.OutputPluginNoteDirective
    .directive_name = 'grrOutputPluginNote';


});
