'use strict';

goog.provide('grrUi.config.module');

goog.require('grrUi.config.binariesListDirective.BinariesListDirective');
goog.require('grrUi.config.configBinariesViewDirective.ConfigBinariesViewDirective');
goog.require('grrUi.config.configViewDirective.ConfigViewDirective');

goog.require('grrUi.core.module');


/**
 * Angular module for config-related UI.
 */
grrUi.config.module = angular.module('grrUi.config', [grrUi.core.module.name]);


grrUi.config.module.directive(
    grrUi.config.binariesListDirective.BinariesListDirective.directive_name,
    grrUi.config.binariesListDirective.BinariesListDirective);
grrUi.config.module.directive(
    grrUi.config.configBinariesViewDirective.ConfigBinariesViewDirective
        .directive_name,
    grrUi.config.configBinariesViewDirective.ConfigBinariesViewDirective);
grrUi.config.module.directive(
    grrUi.config.configViewDirective.ConfigViewDirective.directive_name,
    grrUi.config.configViewDirective.ConfigViewDirective);
