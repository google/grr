'use strict';

goog.provide('grrUi.core.module');

goog.require('grrUi.core.aff4ItemsProviderDirective.Aff4ItemsProviderDirective');
goog.require('grrUi.core.aff4Service.Aff4Service');
goog.require('grrUi.core.apiItemsProviderDirective.ApiItemsProviderDirective');
goog.require('grrUi.core.apiService.ApiService');
goog.require('grrUi.core.infiniteTableDirective.InfiniteTableDirective');
goog.require('grrUi.core.legacyRendererDirective.LegacyRendererDirective');
goog.require('grrUi.core.memoryItemsProviderDirective.MemoryItemsProviderDirective');
goog.require('grrUi.core.pagedFilteredTableDirective.PagedFilteredTableDirective');
goog.require('grrUi.core.pagedFilteredTableDirective.TableBottomDirective');
goog.require('grrUi.core.pagedFilteredTableDirective.TableTopDirective');
goog.require('grrUi.core.reflectionService.ReflectionService');
goog.require('grrUi.core.splitterDirective.SplitterDirective');
goog.require('grrUi.core.splitterDirective.SplitterPaneDirective');


/**
 * Angular module for core GRR UI components.
 */
grrUi.core.module = angular.module('grrUi.core', ['ui.bootstrap']);


grrUi.core.module.directive(
    grrUi.core.apiItemsProviderDirective.
        ApiItemsProviderDirective.directive_name,
    grrUi.core.apiItemsProviderDirective.ApiItemsProviderDirective);
grrUi.core.module.directive(
    grrUi.core.aff4ItemsProviderDirective.
        Aff4ItemsProviderDirective.directive_name,
    grrUi.core.aff4ItemsProviderDirective.Aff4ItemsProviderDirective);
grrUi.core.module.directive(
    grrUi.core.legacyRendererDirective.LegacyRendererDirective.directive_name,
    grrUi.core.legacyRendererDirective.LegacyRendererDirective);
grrUi.core.module.directive(
    grrUi.core.memoryItemsProviderDirective.
        MemoryItemsProviderDirective.directive_name,
    grrUi.core.memoryItemsProviderDirective.MemoryItemsProviderDirective);
grrUi.core.module.directive(
    grrUi.core.pagedFilteredTableDirective.
        PagedFilteredTableDirective.directive_name,
    grrUi.core.pagedFilteredTableDirective.PagedFilteredTableDirective);
grrUi.core.module.directive(
    grrUi.core.pagedFilteredTableDirective.TableTopDirective.directive_name,
    grrUi.core.pagedFilteredTableDirective.TableTopDirective);
grrUi.core.module.directive(
    grrUi.core.pagedFilteredTableDirective.TableBottomDirective.directive_name,
    grrUi.core.pagedFilteredTableDirective.TableBottomDirective);
grrUi.core.module.directive(
    grrUi.core.infiniteTableDirective.InfiniteTableDirective.directive_name,
    grrUi.core.infiniteTableDirective.InfiniteTableDirective);
grrUi.core.module.service(
    grrUi.core.aff4Service.Aff4Service.service_name,
    grrUi.core.aff4Service.Aff4Service);
grrUi.core.module.service(
    grrUi.core.apiService.ApiService.service_name,
    grrUi.core.apiService.ApiService);
grrUi.core.module.directive(
    grrUi.core.splitterDirective.SplitterDirective.directive_name,
    grrUi.core.splitterDirective.SplitterDirective);
grrUi.core.module.directive(
    grrUi.core.splitterDirective.SplitterPaneDirective.directive_name,
    grrUi.core.splitterDirective.SplitterPaneDirective);
grrUi.core.module.service(
    grrUi.core.reflectionService.ReflectionService.service_name,
    grrUi.core.reflectionService.ReflectionService);
