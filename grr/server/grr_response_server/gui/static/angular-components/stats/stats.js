goog.module('grrUi.stats.stats');
goog.module.declareLegacyNamespace();

const {AuditChartDirective} = goog.require('grrUi.stats.auditChartDirective');
const {ChartDirective} = goog.require('grrUi.stats.chartDirective');
const {ComparisonChartDirective} = goog.require('grrUi.stats.comparisonChartDirective');
const {LineChartDirective} = goog.require('grrUi.stats.lineChartDirective');
const {ReportDescsService} = goog.require('grrUi.stats.reportDescsService');
const {ReportDirective} = goog.require('grrUi.stats.reportDirective');
const {ReportListingDirective} = goog.require('grrUi.stats.reportListingDirective');
const {StatsViewDirective} = goog.require('grrUi.stats.statsViewDirective');
const {TimeseriesGraphDirective} = goog.require('grrUi.stats.timeseriesGraphDirective');
const {coreModule} = goog.require('grrUi.core.core');


/**
 * Angular module for stats-related UI.
 */
exports.statsModule = angular.module('grrUi.stats', [coreModule.name]);


exports.statsModule.directive(
    AuditChartDirective.directive_name, AuditChartDirective);
exports.statsModule.directive(ComparisonChartDirective.directive_name,
                              ComparisonChartDirective);
exports.statsModule.directive(ChartDirective.directive_name, ChartDirective);
exports.statsModule.directive(LineChartDirective.directive_name,
                              LineChartDirective);
exports.statsModule.directive(ReportDirective.directive_name, ReportDirective);
exports.statsModule.directive(
    ReportListingDirective.directive_name, ReportListingDirective);
exports.statsModule.directive(
    StatsViewDirective.directive_name, StatsViewDirective);
exports.statsModule.directive(
    TimeseriesGraphDirective.directive_name, TimeseriesGraphDirective);
exports.statsModule.service(
    ReportDescsService.service_name, ReportDescsService);
