goog.module('grrUi.outputPlugins.outputPluginNoteDirective');
goog.module.declareLegacyNamespace();

const semanticRegistryService = goog.requireType('grrUi.core.semanticRegistryService');



/**
 * Controller for OutputPluginNoteDirective.
 * @unrestricted
 */
const OutputPluginNoteController = class {
  /**
   * @param {!angular.Scope} $scope
   * @param {!semanticRegistryService.SemanticRegistryService}
   *     grrOutputPluginsDirectivesRegistryService
   * @ngInject
   */
  constructor($scope, grrOutputPluginsDirectivesRegistryService) {
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

    /**
     * @private {!semanticRegistryService.SemanticRegistryService}
     */
    this.grrOutputPluginsDirectivesRegistryService_ =
        grrOutputPluginsDirectivesRegistryService;

    this.scope_.$watchGroup(
        ['outputPlugin', 'outputPluginsUrl'],
        this.onOutputPluginChange_.bind(this));
  }

  /**
   * Handles changes in descriptor or state.
   *
   * @private
   */
  onOutputPluginChange_() {
    if (angular.isDefined(this.scope_['outputPlugin']) &&
        angular.isDefined(this.scope_['outputPluginsUrl'])) {
      var descriptor =
          this.scope_['outputPlugin']['value']['plugin_descriptor'];
      var pluginName = descriptor['value']['plugin_name']['value'];

      var directive =
          this.grrOutputPluginsDirectivesRegistryService_.findDirectiveForMro(
              [pluginName]);
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
  }
};



/**
 * Directive for displaying notes for output plugins of a flow or hunt.
 *
 * @return {!angular.Directive} Directive definition object.
 * @ngInject
 * @export
 */
exports.OutputPluginNoteDirective = function() {
  return {
    scope: {outputPluginsUrl: '=', outputPlugin: '='},
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
exports.OutputPluginNoteDirective.directive_name = 'grrOutputPluginNote';
