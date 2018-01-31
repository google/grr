'use strict';

goog.provide('grrUi.config');
goog.provide('grrUi.config.configModule');

goog.require('grrUi.config.binariesListDirective.BinariesListDirective');
goog.require('grrUi.config.configBinariesViewDirective.ConfigBinariesViewDirective');
goog.require('grrUi.config.configViewDirective.ConfigViewDirective');

goog.require('grrUi.core.coreModule');


/**
 * Angular module for config-related UI.
 */
grrUi.config.configModule = angular.module('grrUi.config', [grrUi.core.coreModule.name]);


grrUi.config.configModule.directive(
    grrUi.config.binariesListDirective.BinariesListDirective.directive_name,
    grrUi.config.binariesListDirective.BinariesListDirective);
grrUi.config.configModule.directive(
    grrUi.config.configBinariesViewDirective.ConfigBinariesViewDirective
        .directive_name,
    grrUi.config.configBinariesViewDirective.ConfigBinariesViewDirective);
grrUi.config.configModule.directive(
    grrUi.config.configViewDirective.ConfigViewDirective.directive_name,
    grrUi.config.configViewDirective.ConfigViewDirective);
