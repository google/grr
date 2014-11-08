'use strict';

goog.provide('grrUi.hunt.module');

goog.require('grrUi.core.module');
goog.require('grrUi.hunt.huntErrorsDirective.HuntErrorsDirective');
goog.require('grrUi.hunt.huntLogDirective.HuntLogDirective');


/**
 * Angular module for hunts-related UI.
 */
grrUi.hunt.module = angular.module('grrUi.hunt', [grrUi.core.module.name]);


grrUi.hunt.module.directive(
    grrUi.hunt.huntLogDirective.HuntLogDirective.directive_name,
    grrUi.hunt.huntLogDirective.HuntLogDirective);
grrUi.hunt.module.directive(
    grrUi.hunt.huntErrorsDirective.HuntErrorsDirective.directive_name,
    grrUi.hunt.huntErrorsDirective.HuntErrorsDirective);
