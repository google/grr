goog.provide('grrUi.semantic.rekall.module');

goog.require('grrUi.core.module');

goog.require('grrUi.semantic.rekall.logDirective.LogDirective');
goog.require('grrUi.semantic.rekall.metadataDirective.MetadataDirective');
goog.require('grrUi.semantic.rekall.registeredUnixTimeStampDirective.RegisteredUnixTimeStampDirective');
goog.require('grrUi.semantic.rekall.rekallDefaultValueDirective.RekallDefaultValueDirective');
goog.require('grrUi.semantic.rekall.rekallJsonDirective.RekallJsonDirective');
goog.require('grrUi.semantic.rekall.rekallRegistry.RekallRegistryService');
goog.require('grrUi.semantic.rekall.rekallValueDirective.RekallValueDirective');
goog.require('grrUi.semantic.rekall.tableDirective.TableDirective');


/**
 * Module with directives that render Rekall messages.
 */
grrUi.semantic.rekall.module = angular.module('grrUi.semantic.rekall',
                                       [grrUi.core.module.name,
                                        'ui.bootstrap']);

grrUi.semantic.rekall.module.directive(
    grrUi.semantic.rekall.logDirective.LogDirective.directive_name,
    grrUi.semantic.rekall.logDirective.LogDirective);
grrUi.semantic.rekall.module.directive(
    grrUi.semantic.rekall.metadataDirective.MetadataDirective.directive_name,
    grrUi.semantic.rekall.metadataDirective.MetadataDirective);
grrUi.semantic.rekall.module.directive(
    grrUi.semantic.rekall.registeredUnixTimeStampDirective.RegisteredUnixTimeStampDirective.directive_name,
    grrUi.semantic.rekall.registeredUnixTimeStampDirective.RegisteredUnixTimeStampDirective);
grrUi.semantic.rekall.module.directive(
    grrUi.semantic.rekall.rekallDefaultValueDirective.RekallDefaultValueDirective.directive_name,
    grrUi.semantic.rekall.rekallDefaultValueDirective.RekallDefaultValueDirective);
grrUi.semantic.rekall.module.directive(
    grrUi.semantic.rekall.rekallJsonDirective.RekallJsonDirective.directive_name,
    grrUi.semantic.rekall.rekallJsonDirective.RekallJsonDirective);
grrUi.semantic.rekall.module.directive(
    grrUi.semantic.rekall.rekallValueDirective.RekallValueDirective.directive_name,
    grrUi.semantic.rekall.rekallValueDirective.RekallValueDirective);
grrUi.semantic.rekall.module.directive(
    grrUi.semantic.rekall.tableDirective.TableDirective.directive_name,
    grrUi.semantic.rekall.tableDirective.TableDirective);

grrUi.semantic.rekall.module.service(
    grrUi.semantic.rekall.rekallRegistry.RekallRegistryService.service_name,
    grrUi.semantic.rekall.rekallRegistry.RekallRegistryService);

grrUi.semantic.rekall.module.run(function(grrRekallDirectivesRegistryService) {
  var registry = grrRekallDirectivesRegistryService;

  registry.registerDirective(
      grrUi.semantic.rekall.registeredUnixTimeStampDirective.RegisteredUnixTimeStampDirective.rekall_type,
      grrUi.semantic.rekall.registeredUnixTimeStampDirective.RegisteredUnixTimeStampDirective);
});
