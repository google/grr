'use strict';

goog.module('grrUi.outputPlugins.outputPlugins');
goog.module.declareLegacyNamespace();

const {OutputPluginLogsDirective} = goog.require('grrUi.outputPlugins.outputPluginLogsDirective');
const {OutputPluginNoteBodyDirective} = goog.require('grrUi.outputPlugins.outputPluginNoteBodyDirective');
const {OutputPluginNoteDirective} = goog.require('grrUi.outputPlugins.outputPluginNoteDirective');
const {OutputPluginsNotesDirective} = goog.require('grrUi.outputPlugins.outputPluginsNotesDirective');
const {SemanticRegistryService} = goog.require('grrUi.core.semanticRegistryService');
const {coreModule} = goog.require('grrUi.core.core');


/**
 * Module with directives related to flows/hunts output plugins.
 */
exports.outputPluginsModule =
    angular.module('grrUi.outputPlugins', [coreModule.name, 'ui.bootstrap']);

exports.outputPluginsModule.directive(
    OutputPluginsNotesDirective.directive_name, OutputPluginsNotesDirective);
exports.outputPluginsModule.directive(
    OutputPluginLogsDirective.directive_name, OutputPluginLogsDirective);
exports.outputPluginsModule.directive(
    OutputPluginNoteDirective.directive_name, OutputPluginNoteDirective);
exports.outputPluginsModule.directive(
    OutputPluginNoteBodyDirective.directive_name,
    OutputPluginNoteBodyDirective);


exports.outputPluginsModule.service(
    SemanticRegistryService.output_plugins_service_name,
    SemanticRegistryService);


exports.outputPluginsModule.run(function(
    grrOutputPluginsDirectivesRegistryService) {
  // TODO(user): Output plugins directives should be registered here.
  // Use the template below to register new plugins.
  //
  // var registry = grrOutputPluginsDirectivesRegistryService;
  // registry.registerDirective(
  //     grrUi.outputPlugins.<plugin directive>.output_plugin_type,
  //     grrUi.outputPlugins.<plugin directive>);
});
