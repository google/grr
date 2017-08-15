'use strict';

goog.provide('grrUi.outputPlugins.module');

goog.require('grrUi.core.module');
goog.require('grrUi.core.semanticRegistry.SemanticRegistryService');
goog.require('grrUi.outputPlugins.outputPluginLogsDirective.OutputPluginLogsDirective');
goog.require('grrUi.outputPlugins.outputPluginNoteBodyDirective.OutputPluginNoteBodyDirective');
goog.require('grrUi.outputPlugins.outputPluginNoteDirective.OutputPluginNoteDirective');
goog.require('grrUi.outputPlugins.outputPluginsNotesDirective.OutputPluginsNotesDirective');


/**
 * Module with directives related to flows/hunts output plugins.
 */
grrUi.outputPlugins.module = angular.module('grrUi.outputPlugins',
                                            [grrUi.core.module.name,
                                             'ui.bootstrap']);

grrUi.outputPlugins.module.directive(
    grrUi.outputPlugins.outputPluginsNotesDirective
        .OutputPluginsNotesDirective.directive_name,
    grrUi.outputPlugins.outputPluginsNotesDirective
        .OutputPluginsNotesDirective);
grrUi.outputPlugins.module.directive(
    grrUi.outputPlugins.outputPluginLogsDirective
        .OutputPluginLogsDirective.directive_name,
    grrUi.outputPlugins.outputPluginLogsDirective
        .OutputPluginLogsDirective);
grrUi.outputPlugins.module.directive(
    grrUi.outputPlugins.outputPluginNoteDirective
        .OutputPluginNoteDirective.directive_name,
    grrUi.outputPlugins.outputPluginNoteDirective
        .OutputPluginNoteDirective);
grrUi.outputPlugins.module.directive(
    grrUi.outputPlugins.outputPluginNoteBodyDirective
        .OutputPluginNoteBodyDirective.directive_name,
    grrUi.outputPlugins.outputPluginNoteBodyDirective
        .OutputPluginNoteBodyDirective);


grrUi.outputPlugins.module.service(
    grrUi.core.semanticRegistry.SemanticRegistryService
        .output_plugins_service_name,
    grrUi.core.semanticRegistry.SemanticRegistryService);


grrUi.outputPlugins.module.run(function(
    grrOutputPluginsDirectivesRegistryService) {
  // TODO(user): Output plugins directives should be registered here.
  // Use the template below to register new plugins.
  //
  // var registry = grrOutputPluginsDirectivesRegistryService;
  // registry.registerDirective(
  //     grrUi.outputPlugins.<plugin directive>.output_plugin_type,
  //     grrUi.outputPlugins.<plugin directive>);
});
