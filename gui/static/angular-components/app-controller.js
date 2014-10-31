'use strict';

goog.provide('grrUi.appController.module');

goog.require('grrUi.core.module');
goog.require('grrUi.flow.module');
goog.require('grrUi.hunt.module');
goog.require('grrUi.semantic.module');


/**
 * Main GRR UI application module.
 */
grrUi.appController.module = angular.module('grrUi.appController',
                                            [grrUi.core.module.name,
                                             grrUi.hunt.module.name,
                                             grrUi.flow.module.name,
                                             grrUi.semantic.module.name]);

grrUi.appController.module.controller('GrrUiAppController', function() {});
