'use strict';

// TODO(user): Auto-generate parts of this file
//
goog.provide('grrUi.semantic.module');

goog.require('grrUi.core.module');
goog.require('grrUi.core.semanticRegistry.SemanticRegistryService');
goog.require('grrUi.semantic.clientUrnDirective.ClientUrnDirective');
goog.require('grrUi.semantic.fetchMoreLinkDirective.FetchMoreLinkDirective');
goog.require('grrUi.semantic.macAddressDirective.MacAddressDirective');
goog.require('grrUi.semantic.networkAddressDirective.NetworkAddressDirective');
goog.require('grrUi.semantic.objectLabelDirective.ObjectLabelDirective');
goog.require('grrUi.semantic.objectLabelsListDirective.ObjectLabelsListDirective');
goog.require('grrUi.semantic.semanticProtoDirective.SemanticProtoDirective');
goog.require('grrUi.semantic.semanticValueDirective.SemanticValueDirective');
goog.require('grrUi.semantic.timestampDirective.TimestampDirective');


/**
 * Module with directives that render semantic values (i.e. RDFValues) fetched
 * from the server.
 */
grrUi.semantic.module = angular.module('grrUi.semantic',
                                       [grrUi.core.module.name,
                                        'ui.bootstrap']);


grrUi.semantic.module.directive(
    grrUi.semantic.clientUrnDirective.ClientUrnDirective.directive_name,
    grrUi.semantic.clientUrnDirective.ClientUrnDirective);
grrUi.semantic.module.directive(
    grrUi.semantic.fetchMoreLinkDirective.FetchMoreLinkDirective.directive_name,
    grrUi.semantic.fetchMoreLinkDirective.FetchMoreLinkDirective);
grrUi.semantic.module.directive(
    grrUi.semantic.macAddressDirective.MacAddressDirective.directive_name,
    grrUi.semantic.macAddressDirective.MacAddressDirective);
grrUi.semantic.module.directive(
    grrUi.semantic.networkAddressDirective.
        NetworkAddressDirective.directive_name,
    grrUi.semantic.networkAddressDirective.NetworkAddressDirective);
grrUi.semantic.module.directive(
    grrUi.semantic.objectLabelDirective.ObjectLabelDirective.directive_name,
    grrUi.semantic.objectLabelDirective.ObjectLabelDirective);
grrUi.semantic.module.directive(
    grrUi.semantic.objectLabelsListDirective.ObjectLabelsListDirective
        .directive_name,
    grrUi.semantic.objectLabelsListDirective.ObjectLabelsListDirective);
grrUi.semantic.module.directive(
    grrUi.semantic.semanticProtoDirective.SemanticProtoDirective.directive_name,
    grrUi.semantic.semanticProtoDirective.SemanticProtoDirective);
grrUi.semantic.module.directive(
    grrUi.semantic.semanticValueDirective.SemanticValueDirective.directive_name,
    grrUi.semantic.semanticValueDirective.SemanticValueDirective);
grrUi.semantic.module.directive(
    grrUi.semantic.timestampDirective.TimestampDirective.directive_name,
    grrUi.semantic.timestampDirective.TimestampDirective);
grrUi.semantic.module.service(
    grrUi.core.semanticRegistry.SemanticRegistryService.values_service_name,
    grrUi.core.semanticRegistry.SemanticRegistryService);


grrUi.semantic.module.run(function(grrSemanticValueDirectivesRegistryService) {
  var registry = grrSemanticValueDirectivesRegistryService;

  registry.registerDirective(
      grrUi.semantic.clientUrnDirective.ClientUrnDirective.semantic_type,
      grrUi.semantic.clientUrnDirective.ClientUrnDirective);
  registry.registerDirective(
      grrUi.semantic.fetchMoreLinkDirective.FetchMoreLinkDirective
          .semantic_type,
      grrUi.semantic.fetchMoreLinkDirective.FetchMoreLinkDirective);
  registry.registerDirective(
      grrUi.semantic.macAddressDirective.MacAddressDirective.semantic_type,
      grrUi.semantic.macAddressDirective.MacAddressDirective);
  registry.registerDirective(
    grrUi.semantic.networkAddressDirective.NetworkAddressDirective
        .semantic_type,
    grrUi.semantic.networkAddressDirective.NetworkAddressDirective);
  registry.registerDirective(
    grrUi.semantic.objectLabelDirective.ObjectLabelDirective.semantic_type,
    grrUi.semantic.objectLabelDirective.ObjectLabelDirective);
  registry.registerDirective(
    grrUi.semantic.objectLabelDirective.ObjectLabelDirective.semantic_type,
    grrUi.semantic.objectLabelDirective.ObjectLabelDirective);
  registry.registerDirective(
    grrUi.semantic.objectLabelsListDirective.ObjectLabelsListDirective
        .semantic_type,
    grrUi.semantic.objectLabelsListDirective.ObjectLabelsListDirective);
  registry.registerDirective(
    grrUi.semantic.semanticProtoDirective.SemanticProtoDirective.semantic_type,
    grrUi.semantic.semanticProtoDirective.SemanticProtoDirective);
  registry.registerDirective(
    grrUi.semantic.timestampDirective.TimestampDirective.semantic_type,
    grrUi.semantic.timestampDirective.TimestampDirective);
});
