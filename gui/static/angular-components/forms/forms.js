'use strict';

goog.provide('grrUi.forms.module');

goog.require('grrUi.core.module');
goog.require('grrUi.core.semanticRegistry.SemanticRegistryService');
goog.require('grrUi.forms.aff4AttributeFormDirective.Aff4AttributeFormDirective');
goog.require('grrUi.forms.datetimeFormDirective.DatetimeFormDirective');
goog.require('grrUi.forms.dictFormDirective.DictFormDirective');
goog.require('grrUi.forms.globExpressionFormDirective.GlobExpressionFormDirective');
goog.require('grrUi.forms.outputPluginDescriptorFormDirective.OutputPluginDescriptorFormDirective');
goog.require('grrUi.forms.semanticEnumFormDirective.SemanticEnumFormDirective');
goog.require('grrUi.forms.semanticPrimitiveFormDirective.SemanticPrimitiveFormDirective');
goog.require('grrUi.forms.semanticProtoFormDirective.SemanticProtoFormDirective');
goog.require('grrUi.forms.semanticProtoRepeatedFieldFormDirective.SemanticProtoRepeatedFieldFormDirective');
goog.require('grrUi.forms.semanticProtoSingleFieldFormDirective.SemanticProtoSingleFieldFormDirective');
goog.require('grrUi.forms.semanticProtoUnionFormDirective.SemanticProtoUnionFormDirective');
goog.require('grrUi.forms.semanticValueFormDirective.SemanticValueFormDirective');


/**
 * Angular module for forms-related UI.
 */
grrUi.forms.module = angular.module('grrUi.forms', [grrUi.core.module.name,
                                                    'ui.bootstrap']);


grrUi.forms.module.service(
    grrUi.core.semanticRegistry.SemanticRegistryService.forms_service_name,
    grrUi.core.semanticRegistry.SemanticRegistryService);
grrUi.forms.module.service(
    grrUi.core.semanticRegistry.SemanticRegistryService
        .repeated_forms_service_name,
    grrUi.core.semanticRegistry.SemanticRegistryService);


grrUi.forms.module.directive(
    grrUi.forms.aff4AttributeFormDirective.Aff4AttributeFormDirective
        .directive_name,
    grrUi.forms.aff4AttributeFormDirective.Aff4AttributeFormDirective);
grrUi.forms.module.directive(
    grrUi.forms.datetimeFormDirective.DatetimeFormDirective.directive_name,
    grrUi.forms.datetimeFormDirective.DatetimeFormDirective);
grrUi.forms.module.directive(
    grrUi.forms.dictFormDirective.DictFormDirective.directive_name,
    grrUi.forms.dictFormDirective.DictFormDirective);
grrUi.forms.module.directive(
    grrUi.forms.globExpressionFormDirective.GlobExpressionFormDirective
        .directive_name,
    grrUi.forms.globExpressionFormDirective.GlobExpressionFormDirective);
grrUi.forms.module.directive(
    grrUi.forms.outputPluginDescriptorFormDirective
        .OutputPluginDescriptorFormDirective.directive_name,
    grrUi.forms.outputPluginDescriptorFormDirective
        .OutputPluginDescriptorFormDirective);
grrUi.forms.module.directive(
    grrUi.forms.semanticEnumFormDirective.SemanticEnumFormDirective
        .directive_name,
    grrUi.forms.semanticEnumFormDirective.SemanticEnumFormDirective);
grrUi.forms.module.directive(
    grrUi.forms.semanticPrimitiveFormDirective.SemanticPrimitiveFormDirective
        .directive_name,
    grrUi.forms.semanticPrimitiveFormDirective.SemanticPrimitiveFormDirective);
grrUi.forms.module.directive(
    grrUi.forms.semanticProtoFormDirective.SemanticProtoFormDirective
        .directive_name,
    grrUi.forms.semanticProtoFormDirective.SemanticProtoFormDirective);
grrUi.forms.module.directive(
    grrUi.forms.semanticProtoSingleFieldFormDirective
        .SemanticProtoSingleFieldFormDirective.directive_name,
    grrUi.forms.semanticProtoSingleFieldFormDirective
        .SemanticProtoSingleFieldFormDirective);
grrUi.forms.module.directive(
    grrUi.forms.semanticProtoRepeatedFieldFormDirective
        .SemanticProtoRepeatedFieldFormDirective.directive_name,
    grrUi.forms.semanticProtoRepeatedFieldFormDirective
        .SemanticProtoRepeatedFieldFormDirective);
grrUi.forms.module.directive(
    grrUi.forms.semanticProtoUnionFormDirective
        .SemanticProtoUnionFormDirective.directive_name,
    grrUi.forms.semanticProtoUnionFormDirective
        .SemanticProtoUnionFormDirective);
grrUi.forms.module.directive(
    grrUi.forms.semanticValueFormDirective.SemanticValueFormDirective
        .directive_name,
    grrUi.forms.semanticValueFormDirective.SemanticValueFormDirective);


grrUi.forms.module.run(function(grrSemanticFormDirectivesRegistryService) {
  var registry = grrSemanticFormDirectivesRegistryService;

  registry.registerDirective(
      grrUi.forms.aff4AttributeFormDirective.Aff4AttributeFormDirective
          .semantic_type,
      grrUi.forms.aff4AttributeFormDirective.Aff4AttributeFormDirective);
  registry.registerDirective(
      grrUi.forms.datetimeFormDirective.DatetimeFormDirective.semantic_type,
      grrUi.forms.datetimeFormDirective.DatetimeFormDirective);
  var dictSemanticTypes =
      grrUi.forms.dictFormDirective.DictFormDirective.semantic_types;
  angular.forEach(dictSemanticTypes, function(dictSemanticType) {
    registry.registerDirective(
        dictSemanticType,
        grrUi.forms.dictFormDirective.DictFormDirective);
  });

  registry.registerDirective(
      grrUi.forms.globExpressionFormDirective.GlobExpressionFormDirective
          .semantic_type,
      grrUi.forms.globExpressionFormDirective.GlobExpressionFormDirective);

  registry.registerDirective(
      grrUi.forms.outputPluginDescriptorFormDirective
          .OutputPluginDescriptorFormDirective.semantic_type,
      grrUi.forms.outputPluginDescriptorFormDirective
          .OutputPluginDescriptorFormDirective);

  var primitiveSemanticTypes =
      grrUi.forms.semanticPrimitiveFormDirective.SemanticPrimitiveFormDirective
      .semantic_types;
  angular.forEach(primitiveSemanticTypes, function(primitiveSemanticType) {
    registry.registerDirective(
        primitiveSemanticType,
        grrUi.forms.semanticPrimitiveFormDirective.
            SemanticPrimitiveFormDirective);
  });

  registry.registerDirective(
      grrUi.forms.semanticEnumFormDirective.SemanticEnumFormDirective
          .semantic_type,
      grrUi.forms.semanticEnumFormDirective.SemanticEnumFormDirective);
  registry.registerDirective(
      grrUi.forms.semanticProtoFormDirective.SemanticProtoFormDirective
          .semantic_type,
      grrUi.forms.semanticProtoFormDirective.SemanticProtoFormDirective);
});
