'use strict';

goog.module('grrUi.config.config');
goog.module.declareLegacyNamespace();

const {BinariesListDirective} = goog.require('grrUi.config.binariesListDirective');
const {ConfigBinariesViewDirective} = goog.require('grrUi.config.configBinariesViewDirective');
const {ConfigViewDirective} = goog.require('grrUi.config.configViewDirective');
const {coreModule} = goog.require('grrUi.core.core');



/**
 * Angular module for config-related UI.
 */
exports.configModule = angular.module('grrUi.config', [coreModule.name]);


exports.configModule.directive(
    BinariesListDirective.directive_name, BinariesListDirective);
exports.configModule.directive(
    ConfigBinariesViewDirective.directive_name, ConfigBinariesViewDirective);
exports.configModule.directive(
    ConfigViewDirective.directive_name, ConfigViewDirective);
