'use strict';

goog.provide('grrUi.outputPlugins');
goog.provide('grrUi.outputPlugins.outputPluginsModule');

goog.require('grrUi.core');                          // USE: coreModule
goog.require('grrUi.core.semanticRegistryService');  // USE: SemanticRegistryService
goog.require('grrUi.outputPlugins.outputPluginLogsDirective');  // USE: OutputPluginLogsDirective
goog.require('grrUi.outputPlugins.outputPluginNoteBodyDirective');  // USE: OutputPluginNoteBodyDirective
goog.require('grrUi.outputPlugins.outputPluginNoteDirective');  // USE: OutputPluginNoteDirective
goog.require('grrUi.outputPlugins.outputPluginsNotesDirective');  // USE: OutputPluginsNotesDirective


/**
 * Module with directives related to flows/hunts output plugins.
 */
grrUi.outputPlugins.outputPluginsModule = angular.module('grrUi.outputPlugins',
                                            [grrUi.core.coreModule.name,
                                             'ui.bootstrap']);

grrUi.outputPlugins.outputPluginsModule.directive(
    grrUi.outputPlugins.outputPluginsNotesDirective
        .OutputPluginsNotesDirective.directive_name,
    grrUi.outputPlugins.outputPluginsNotesDirective
        .OutputPluginsNotesDirective);
grrUi.outputPlugins.outputPluginsModule.directive(
    grrUi.outputPlugins.outputPluginLogsDirective
        .OutputPluginLogsDirective.directive_name,
    grrUi.outputPlugins.outputPluginLogsDirective
        .OutputPluginLogsDirective);
grrUi.outputPlugins.outputPluginsModule.directive(
    grrUi.outputPlugins.outputPluginNoteDirective
        .OutputPluginNoteDirective.directive_name,
    grrUi.outputPlugins.outputPluginNoteDirective
        .OutputPluginNoteDirective);
grrUi.outputPlugins.outputPluginsModule.directive(
    grrUi.outputPlugins.outputPluginNoteBodyDirective
        .OutputPluginNoteBodyDirective.directive_name,
    grrUi.outputPlugins.outputPluginNoteBodyDirective
        .OutputPluginNoteBodyDirective);


grrUi.outputPlugins.outputPluginsModule.service(
    grrUi.core.semanticRegistryService.SemanticRegistryService
        .output_plugins_service_name,
    grrUi.core.semanticRegistryService.SemanticRegistryService);


grrUi.outputPlugins.outputPluginsModule.run(function(
    grrOutputPluginsDirectivesRegistryService) {
  // TODO(user): Output plugins directives should be registered here.
  // Use the template below to register new plugins.
  //
  // var registry = grrOutputPluginsDirectivesRegistryService;
  // registry.registerDirective(
  //     grrUi.outputPlugins.<plugin directive>.output_plugin_type,
  //     grrUi.outputPlugins.<plugin directive>);
});
