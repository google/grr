'use strict';

goog.provide('grrUi.appController.module');

goog.require('grrUi.artifact.module');
goog.require('grrUi.client.module');
goog.require('grrUi.config.module');
goog.require('grrUi.core.module');
goog.require('grrUi.docs.module');
goog.require('grrUi.flow.module');
goog.require('grrUi.forms.module');
goog.require('grrUi.hunt.module');
goog.require('grrUi.outputPlugins.module');
goog.require('grrUi.semantic.module');
goog.require('grrUi.stats.module');
goog.require('grrUi.user.module');


/**
 * Main GRR UI application module.
 */
grrUi.appController.module = angular.module('grrUi.appController',
                                            [grrUi.artifact.module.name,
                                             grrUi.client.module.name,
                                             grrUi.config.module.name,
                                             grrUi.core.module.name,
                                             grrUi.docs.module.name,
                                             grrUi.flow.module.name,
                                             grrUi.forms.module.name,
                                             grrUi.hunt.module.name,
                                             grrUi.outputPlugins.module.name,
                                             grrUi.semantic.module.name,
                                             grrUi.stats.module.name,
                                             grrUi.user.module.name]);

grrUi.appController.module.controller('GrrUiAppController', function() {});
