'use strict';

goog.provide('grrUi.stats.stats');
goog.provide('grrUi.stats.stats.statsModule');

goog.require('grrUi.core.core');                     // USE: coreModule
goog.require('grrUi.stats.auditChartDirective');     // USE: AuditChartDirective
goog.require('grrUi.stats.chartDirective');          // USE: ChartDirective
goog.require('grrUi.stats.reportDescsService');      // USE: ReportDescsService
goog.require('grrUi.stats.reportDirective');         // USE: ReportDirective
goog.require('grrUi.stats.reportListingDirective');  // USE: ReportListingDirective
goog.require('grrUi.stats.serverLoadDirective');  // USE: ServerLoadDirective, ServerLoadIndicatorService
goog.require('grrUi.stats.serverLoadGraphSerieDirective');  // USE: ServerLoadGraphSerieDirective
goog.require('grrUi.stats.serverLoadIndicatorDirective');  // USE: ServerLoadIndicatorDirective
goog.require('grrUi.stats.statsViewDirective');  // USE: StatsViewDirective
goog.require('grrUi.stats.timeseriesGraphDirective');  // USE: TimeseriesGraphDirective


/**
 * Angular module for stats-related UI.
 */
grrUi.stats.stats.statsModule =
    angular.module('grrUi.stats', [grrUi.core.core.coreModule.name]);


grrUi.stats.stats.statsModule.directive(
    grrUi.stats.auditChartDirective.AuditChartDirective.directive_name,
    grrUi.stats.auditChartDirective.AuditChartDirective);
grrUi.stats.stats.statsModule.directive(
    grrUi.stats.chartDirective.ChartDirective.directive_name,
    grrUi.stats.chartDirective.ChartDirective);
grrUi.stats.stats.statsModule.directive(
    grrUi.stats.reportDirective.ReportDirective.directive_name,
    grrUi.stats.reportDirective.ReportDirective);
grrUi.stats.stats.statsModule.directive(
    grrUi.stats.reportListingDirective.ReportListingDirective.directive_name,
    grrUi.stats.reportListingDirective.ReportListingDirective);
grrUi.stats.stats.statsModule.directive(
    grrUi.stats.serverLoadDirective.ServerLoadDirective.directive_name,
    grrUi.stats.serverLoadDirective.ServerLoadDirective);
grrUi.stats.stats.statsModule.directive(
    grrUi.stats.serverLoadGraphSerieDirective.ServerLoadGraphSerieDirective
        .directive_name,
    grrUi.stats.serverLoadGraphSerieDirective.ServerLoadGraphSerieDirective);
grrUi.stats.stats.statsModule.directive(
    grrUi.stats.serverLoadIndicatorDirective.ServerLoadIndicatorDirective
        .directive_name,
    grrUi.stats.serverLoadIndicatorDirective.ServerLoadIndicatorDirective);
grrUi.stats.stats.statsModule.directive(
    grrUi.stats.statsViewDirective.StatsViewDirective.directive_name,
    grrUi.stats.statsViewDirective.StatsViewDirective);
grrUi.stats.stats.statsModule.directive(
    grrUi.stats.timeseriesGraphDirective.TimeseriesGraphDirective
        .directive_name,
    grrUi.stats.timeseriesGraphDirective.TimeseriesGraphDirective);

grrUi.stats.stats.statsModule.service(
    grrUi.stats.serverLoadDirective.ServerLoadIndicatorService.service_name,
    grrUi.stats.serverLoadDirective.ServerLoadIndicatorService);
grrUi.stats.stats.statsModule.service(
    grrUi.stats.reportDescsService.ReportDescsService.service_name,
    grrUi.stats.reportDescsService.ReportDescsService);
