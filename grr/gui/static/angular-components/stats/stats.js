'use strict';

goog.provide('grrUi.stats.module');

goog.require('grrUi.core.module');
goog.require('grrUi.stats.auditChartDirective.AuditChartDirective');
goog.require('grrUi.stats.chartDirective.ChartDirective');
goog.require('grrUi.stats.reportDescsService.ReportDescsService');
goog.require('grrUi.stats.reportDirective.ReportDirective');
goog.require('grrUi.stats.reportListingDirective.ReportListingDirective');
goog.require('grrUi.stats.serverLoadDirective.ServerLoadDirective');
goog.require('grrUi.stats.serverLoadDirective.ServerLoadIndicatorService');
goog.require('grrUi.stats.serverLoadGraphSerieDirective.ServerLoadGraphSerieDirective');
goog.require('grrUi.stats.serverLoadIndicatorDirective.ServerLoadIndicatorDirective');
goog.require('grrUi.stats.statsViewDirective.StatsViewDirective');
goog.require('grrUi.stats.timeseriesGraphDirective.TimeseriesGraphDirective');


/**
 * Angular module for stats-related UI.
 */
grrUi.stats.module = angular.module('grrUi.stats', [grrUi.core.module.name]);


grrUi.stats.module.directive(
    grrUi.stats.auditChartDirective.AuditChartDirective.directive_name,
    grrUi.stats.auditChartDirective.AuditChartDirective);
grrUi.stats.module.directive(
    grrUi.stats.chartDirective.ChartDirective.directive_name,
    grrUi.stats.chartDirective.ChartDirective);
grrUi.stats.module.directive(
    grrUi.stats.reportDirective.ReportDirective.directive_name,
    grrUi.stats.reportDirective.ReportDirective);
grrUi.stats.module.directive(
    grrUi.stats.reportListingDirective.ReportListingDirective.directive_name,
    grrUi.stats.reportListingDirective.ReportListingDirective);
grrUi.stats.module.directive(
    grrUi.stats.serverLoadDirective.ServerLoadDirective.directive_name,
    grrUi.stats.serverLoadDirective.ServerLoadDirective);
grrUi.stats.module.directive(
    grrUi.stats.serverLoadGraphSerieDirective.ServerLoadGraphSerieDirective.
        directive_name,
    grrUi.stats.serverLoadGraphSerieDirective.ServerLoadGraphSerieDirective);
grrUi.stats.module.directive(
    grrUi.stats.serverLoadIndicatorDirective.ServerLoadIndicatorDirective.
        directive_name,
    grrUi.stats.serverLoadIndicatorDirective.ServerLoadIndicatorDirective);
grrUi.stats.module.directive(
    grrUi.stats.statsViewDirective.StatsViewDirective.directive_name,
    grrUi.stats.statsViewDirective.StatsViewDirective);
grrUi.stats.module.directive(
    grrUi.stats.timeseriesGraphDirective.TimeseriesGraphDirective
        .directive_name,
    grrUi.stats.timeseriesGraphDirective.TimeseriesGraphDirective);

grrUi.stats.module.service(
    grrUi.stats.serverLoadDirective.ServerLoadIndicatorService.service_name,
    grrUi.stats.serverLoadDirective.ServerLoadIndicatorService);
grrUi.stats.module.service(
    grrUi.stats.reportDescsService.ReportDescsService.service_name,
    grrUi.stats.reportDescsService.ReportDescsService);
