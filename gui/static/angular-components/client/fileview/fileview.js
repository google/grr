'use strict';

goog.provide('grrUi.client.fileview.module');
goog.require('grrUi.client.fileview.recursiveListButtonDirective.RecursiveListButtonDirective');
goog.require('grrUi.core.module');


/**
 * Angular module for clients-related UI.
 */
grrUi.client.fileview.module = angular.module('grrUi.client.fileview',
                                              [grrUi.core.module.name]);

grrUi.client.fileview.module.directive(
    grrUi.client.fileview.recursiveListButtonDirective
        .RecursiveListButtonDirective.directive_name,
    grrUi.client.fileview.recursiveListButtonDirective
        .RecursiveListButtonDirective);
