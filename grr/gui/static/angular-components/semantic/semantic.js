'use strict';

goog.module('grrUi.semantic.semantic');
goog.module.declareLegacyNamespace();

const {ApiHuntResultDirective} = goog.require('grrUi.semantic.apiHuntResultDirective');
const {ByteSizeDirective} = goog.require('grrUi.semantic.byteSizeDirective');
const {BytesDirective} = goog.require('grrUi.semantic.bytesDirective');
const {ClientUrnDirective} = goog.require('grrUi.semantic.clientUrnDirective');
const {DataObjectDirective} = goog.require('grrUi.semantic.dataObjectDirective');
const {DictDirective} = goog.require('grrUi.semantic.dictDirective');
const {DurationDirective} = goog.require('grrUi.semantic.durationDirective');
const {EncryptionKeyDirective} = goog.require('grrUi.semantic.encryptionKeyDirective');
const {FlowIdDirective} = goog.require('grrUi.semantic.flowIdDirective');
const {HashDigestDirective} = goog.require('grrUi.semantic.hashDigestDirective');
const {HashListDirective} = goog.require('grrUi.semantic.hashListDirective');
const {HuntIdDirective} = goog.require('grrUi.semantic.huntIdDirective');
const {JsonDirective} = goog.require('grrUi.semantic.jsonDirective');
const {MacAddressDirective} = goog.require('grrUi.semantic.macAddressDirective');
const {NetworkAddressDirective} = goog.require('grrUi.semantic.networkAddressDirective');
const {ObjectLabelDirective} = goog.require('grrUi.semantic.objectLabelDirective');
const {ObjectLabelsListDirective} = goog.require('grrUi.semantic.objectLabelsListDirective');
const {PrimitiveDirective} = goog.require('grrUi.semantic.primitiveDirective');
const {RegistryOverrideDirective, SemanticValueDirective} = goog.require('grrUi.semantic.semanticValueDirective');
const {RekallResponseDirective} = goog.require('grrUi.semantic.rekallResponseDirective');
const {SemanticDiffAnnotatedProtoDirective} = goog.require('grrUi.semantic.semanticDiffAnnotatedProtoDirective');
const {SemanticProtoDirective} = goog.require('grrUi.semantic.semanticProtoDirective');
const {SemanticProtosDiffDirective} = goog.require('grrUi.semantic.semanticProtosDiffDirective');
const {SemanticRegistryService} = goog.require('grrUi.core.semanticRegistryService');
const {SemanticVersionedProtoDirective} = goog.require('grrUi.semantic.semanticVersionedProtoDirective');
const {StatEntryDirective} = goog.require('grrUi.semantic.statEntryDirective');
const {StatExtFlagsLinuxDirective} = goog.require('grrUi.semantic.statExtFlagsLinuxDirective');
const {StatExtFlagsOsxDirective} = goog.require('grrUi.semantic.statExtFlagsOsxDirective');
const {StatModeDirective} = goog.require('grrUi.semantic.statModeDirective');
const {TimestampDirective} = goog.require('grrUi.semantic.timestampDirective');
const {TimestampSecondsDirective} = goog.require('grrUi.semantic.timestampSecondsDirective');
const {UrnDirective} = goog.require('grrUi.semantic.urnDirective');
const {coreModule} = goog.require('grrUi.core.core');
const {pseudoModule} = goog.require('grrUi.semantic.pseudo.pseudo');
const {rekallModule} = goog.require('grrUi.semantic.rekall.rekall');
const {routingModule} = goog.require('grrUi.routing.routing');

// TODO(user): Auto-generate parts of this file
//


/**
 * Module with directives that render semantic values (i.e. RDFValues) fetched
 * from the server.
 */
exports.semanticModule = angular.module('grrUi.semantic', [
  coreModule.name, routingModule.name, pseudoModule.name, rekallModule.name,
  'ui.bootstrap'
]);

exports.semanticModule.directive(
    ApiHuntResultDirective.directive_name, ApiHuntResultDirective);
exports.semanticModule.directive(
    ByteSizeDirective.directive_name, ByteSizeDirective);
exports.semanticModule.directive(BytesDirective.directive_name, BytesDirective);
exports.semanticModule.directive(
    ClientUrnDirective.directive_name, ClientUrnDirective);
exports.semanticModule.directive(
    DataObjectDirective.directive_name, DataObjectDirective);
exports.semanticModule.directive(DictDirective.directive_name, DictDirective);
exports.semanticModule.directive(
    DurationDirective.directive_name, DurationDirective);
exports.semanticModule.directive(
    EncryptionKeyDirective.directive_name, EncryptionKeyDirective);
exports.semanticModule.directive(
    FlowIdDirective.directive_name, FlowIdDirective);
exports.semanticModule.directive(
    HashDigestDirective.directive_name, HashDigestDirective);
exports.semanticModule.directive(
    HashListDirective.directive_name, HashListDirective);
exports.semanticModule.directive(
    HuntIdDirective.directive_name, HuntIdDirective);
exports.semanticModule.directive(JsonDirective.directive_name, JsonDirective);
exports.semanticModule.directive(
    MacAddressDirective.directive_name, MacAddressDirective);
exports.semanticModule.directive(
    NetworkAddressDirective.directive_name, NetworkAddressDirective);
exports.semanticModule.directive(
    ObjectLabelDirective.directive_name, ObjectLabelDirective);
exports.semanticModule.directive(
    ObjectLabelsListDirective.directive_name, ObjectLabelsListDirective);
exports.semanticModule.directive(
    PrimitiveDirective.directive_name, PrimitiveDirective);

exports.semanticModule.directive(
    RekallResponseDirective.directive_name, RekallResponseDirective);

exports.semanticModule.directive(
    SemanticDiffAnnotatedProtoDirective.directive_name,
    SemanticDiffAnnotatedProtoDirective);
exports.semanticModule.directive(
    SemanticProtoDirective.directive_name, SemanticProtoDirective);
exports.semanticModule.directive(
    RegistryOverrideDirective.directive_name, RegistryOverrideDirective);
exports.semanticModule.directive(
    SemanticValueDirective.directive_name, SemanticValueDirective);
exports.semanticModule.directive(
    SemanticProtosDiffDirective.directive_name, SemanticProtosDiffDirective);
exports.semanticModule.directive(
    SemanticVersionedProtoDirective.directive_name,
    SemanticVersionedProtoDirective);
exports.semanticModule.directive(
    StatEntryDirective.directive_name, StatEntryDirective);
exports.semanticModule.directive(
    StatExtFlagsLinuxDirective.directive_name, StatExtFlagsLinuxDirective);
exports.semanticModule.directive(
    StatExtFlagsOsxDirective.directive_name, StatExtFlagsOsxDirective);
exports.semanticModule.directive(
    StatModeDirective.directive_name, StatModeDirective);
exports.semanticModule.directive(
    TimestampDirective.directive_name, TimestampDirective);
exports.semanticModule.directive(
    TimestampSecondsDirective.directive_name, TimestampSecondsDirective);
exports.semanticModule.directive(UrnDirective.directive_name, UrnDirective);

exports.semanticModule.service(
    SemanticRegistryService.values_service_name, SemanticRegistryService);


exports.semanticModule.run(function(grrSemanticValueDirectivesRegistryService) {
  var registry = grrSemanticValueDirectivesRegistryService;

  registry.registerDirective(
      ApiHuntResultDirective.semantic_type, ApiHuntResultDirective);
  registry.registerDirective(
      ByteSizeDirective.semantic_type, ByteSizeDirective);
  angular.forEach(BytesDirective.semantic_types, function(type) {
    registry.registerDirective(type, BytesDirective);
  }.bind(this));
  angular.forEach(ClientUrnDirective.semantic_types, function(type) {
    registry.registerDirective(type, ClientUrnDirective);
  }.bind(this));
  registry.registerDirective(
      DataObjectDirective.semantic_type, DataObjectDirective);
  angular.forEach(DictDirective.semantic_types, function(type) {
    registry.registerDirective(type, DictDirective);
  }.bind(this));
  registry.registerDirective(
      DurationDirective.semantic_type, DurationDirective);
  registry.registerDirective(
      EncryptionKeyDirective.semantic_type, EncryptionKeyDirective);
  registry.registerDirective(FlowIdDirective.semantic_type, FlowIdDirective);
  registry.registerDirective(
      HashDigestDirective.semantic_type, HashDigestDirective);
  registry.registerDirective(
      HashListDirective.semantic_type, HashListDirective);
  registry.registerDirective(HuntIdDirective.semantic_type, HuntIdDirective);
  registry.registerDirective(JsonDirective.semantic_type, JsonDirective);
  registry.registerDirective(
      MacAddressDirective.semantic_type, MacAddressDirective);
  registry.registerDirective(
      NetworkAddressDirective.semantic_type, NetworkAddressDirective);
  registry.registerDirective(
      ObjectLabelDirective.semantic_type, ObjectLabelDirective);
  registry.registerDirective(
      ObjectLabelDirective.semantic_type, ObjectLabelDirective);
  registry.registerDirective(
      ObjectLabelsListDirective.semantic_type, ObjectLabelsListDirective);
  angular.forEach(PrimitiveDirective.semantic_types, function(type) {
    registry.registerDirective(type, PrimitiveDirective);
  }.bind(this));
  registry.registerDirective(
      RekallResponseDirective.semantic_type, RekallResponseDirective);
  registry.registerDirective(
      SemanticProtoDirective.semantic_type, SemanticProtoDirective);
  angular.forEach(StatEntryDirective.semantic_types, function(type) {
    registry.registerDirective(type, StatEntryDirective);
  }.bind(this));
  registry.registerDirective(
      StatExtFlagsLinuxDirective.semantic_type, StatExtFlagsLinuxDirective);
  registry.registerDirective(
      StatExtFlagsOsxDirective.semantic_type, StatExtFlagsOsxDirective);
  registry.registerDirective(
      StatModeDirective.semantic_type, StatModeDirective);
  registry.registerDirective(
      TimestampDirective.semantic_type, TimestampDirective);
  registry.registerDirective(
      TimestampSecondsDirective.semantic_type, TimestampSecondsDirective);
  registry.registerDirective(UrnDirective.semantic_type, UrnDirective);
});
