'use strict';

goog.module('grrUi.semantic.rekall.rekall');
goog.module.declareLegacyNamespace();

const {LogDirective} = goog.require('grrUi.semantic.rekall.logDirective');
const {MetadataDirective} = goog.require('grrUi.semantic.rekall.metadataDirective');
const {RegisteredUnixTimeStampDirective} = goog.require('grrUi.semantic.rekall.registeredUnixTimeStampDirective');
const {RekallDefaultValueDirective} = goog.require('grrUi.semantic.rekall.rekallDefaultValueDirective');
const {RekallJsonDirective} = goog.require('grrUi.semantic.rekall.rekallJsonDirective');
const {RekallRegistryService} = goog.require('grrUi.semantic.rekall.rekallRegistryService');
const {RekallValueDirective} = goog.require('grrUi.semantic.rekall.rekallValueDirective');
const {TableDirective} = goog.require('grrUi.semantic.rekall.tableDirective');
const {coreModule} = goog.require('grrUi.core.core');


/**
 * Module with directives that render Rekall messages.
 */
exports.rekallModule =
    angular.module('grrUi.semantic.rekall', [coreModule.name, 'ui.bootstrap']);

exports.rekallModule.directive(LogDirective.directive_name, LogDirective);
exports.rekallModule.directive(
    MetadataDirective.directive_name, MetadataDirective);
exports.rekallModule.directive(
    RegisteredUnixTimeStampDirective.directive_name,
    RegisteredUnixTimeStampDirective);
exports.rekallModule.directive(
    RekallDefaultValueDirective.directive_name, RekallDefaultValueDirective);
exports.rekallModule.directive(
    RekallJsonDirective.directive_name, RekallJsonDirective);
exports.rekallModule.directive(
    RekallValueDirective.directive_name, RekallValueDirective);
exports.rekallModule.directive(TableDirective.directive_name, TableDirective);

exports.rekallModule.service(
    RekallRegistryService.service_name, RekallRegistryService);

exports.rekallModule.run(function(grrRekallDirectivesRegistryService) {
  var registry = grrRekallDirectivesRegistryService;

  registry.registerDirective(
      RegisteredUnixTimeStampDirective.rekall_type,
      RegisteredUnixTimeStampDirective);
});
