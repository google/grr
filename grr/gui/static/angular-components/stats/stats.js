'use strict';

goog.provide('grrUi.stats.module');

goog.require('grrUi.core.module');
goog.require('grrUi.stats.serverLoadDirective.ServerLoadDirective');
goog.require('grrUi.stats.serverLoadDirective.ServerLoadIndicatorService');
goog.require('grrUi.stats.serverLoadGraphDirective.ServerLoadGraphDirective');
goog.require('grrUi.stats.serverLoadGraphDirective.ServerLoadGraphSerieDirective');
goog.require('grrUi.stats.serverLoadIndicatorDirective.ServerLoadIndicatorDirective');
goog.require('grrUi.stats.statsViewDirective.StatsViewDirective');


/**
 * Angular module for stats-related UI.
 */
grrUi.stats.module = angular.module('grrUi.stats', [grrUi.core.module.name]);


grrUi.stats.module.directive(
    grrUi.stats.serverLoadDirective.ServerLoadDirective.directive_name,
    grrUi.stats.serverLoadDirective.ServerLoadDirective);
grrUi.stats.module.directive(
    grrUi.stats.serverLoadGraphDirective.ServerLoadGraphDirective.
        directive_name,
    grrUi.stats.serverLoadGraphDirective.ServerLoadGraphDirective);
grrUi.stats.module.directive(
    grrUi.stats.serverLoadGraphDirective.ServerLoadGraphSerieDirective.
        directive_name,
    grrUi.stats.serverLoadGraphDirective.ServerLoadGraphSerieDirective);
grrUi.stats.module.directive(
    grrUi.stats.serverLoadIndicatorDirective.ServerLoadIndicatorDirective.
        directive_name,
    grrUi.stats.serverLoadIndicatorDirective.ServerLoadIndicatorDirective);
grrUi.stats.module.directive(
    grrUi.stats.statsViewDirective.StatsViewDirective.directive_name,
    grrUi.stats.statsViewDirective.StatsViewDirective);

grrUi.stats.module.service(
    grrUi.stats.serverLoadDirective.ServerLoadIndicatorService.service_name,
    grrUi.stats.serverLoadDirective.ServerLoadIndicatorService);
