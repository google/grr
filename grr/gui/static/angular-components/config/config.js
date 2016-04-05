'use strict';

goog.provide('grrUi.config.module');

goog.require('grrUi.config.configViewDirective.ConfigViewDirective');
goog.require('grrUi.core.module');


/**
 * Angular module for config-related UI.
 */
grrUi.config.module = angular.module('grrUi.config', [grrUi.core.module.name]);


grrUi.config.module.directive(
    grrUi.config.configViewDirective.ConfigViewDirective.directive_name,
    grrUi.config.configViewDirective.ConfigViewDirective);
