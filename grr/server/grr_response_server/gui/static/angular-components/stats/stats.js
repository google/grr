'use strict';

goog.module('grrUi.stats.stats');
goog.module.declareLegacyNamespace();

const {AuditChartDirective} = goog.require('grrUi.stats.auditChartDirective');
const {ChartDirective} = goog.require('grrUi.stats.chartDirective');
const {ReportDescsService} = goog.require('grrUi.stats.reportDescsService');
const {ReportDirective} = goog.require('grrUi.stats.reportDirective');
const {ReportListingDirective} = goog.require('grrUi.stats.reportListingDirective');
const {ServerLoadDirective, ServerLoadIndicatorService} = goog.require('grrUi.stats.serverLoadDirective');
const {ServerLoadGraphSerieDirective} = goog.require('grrUi.stats.serverLoadGraphSerieDirective');
const {ServerLoadIndicatorDirective} = goog.require('grrUi.stats.serverLoadIndicatorDirective');
const {StatsViewDirective} = goog.require('grrUi.stats.statsViewDirective');
const {TimeseriesGraphDirective} = goog.require('grrUi.stats.timeseriesGraphDirective');
const {coreModule} = goog.require('grrUi.core.core');


/**
 * Angular module for stats-related UI.
 */
exports.statsModule = angular.module('grrUi.stats', [coreModule.name]);


exports.statsModule.directive(
    AuditChartDirective.directive_name, AuditChartDirective);
exports.statsModule.directive(ChartDirective.directive_name, ChartDirective);
exports.statsModule.directive(ReportDirective.directive_name, ReportDirective);
exports.statsModule.directive(
    ReportListingDirective.directive_name, ReportListingDirective);
exports.statsModule.directive(
    ServerLoadDirective.directive_name, ServerLoadDirective);
exports.statsModule.directive(
    ServerLoadGraphSerieDirective.directive_name,
    ServerLoadGraphSerieDirective);
exports.statsModule.directive(
    ServerLoadIndicatorDirective.directive_name, ServerLoadIndicatorDirective);
exports.statsModule.directive(
    StatsViewDirective.directive_name, StatsViewDirective);
exports.statsModule.directive(
    TimeseriesGraphDirective.directive_name, TimeseriesGraphDirective);

exports.statsModule.service(
    ServerLoadIndicatorService.service_name, ServerLoadIndicatorService);
exports.statsModule.service(
    ReportDescsService.service_name, ReportDescsService);
