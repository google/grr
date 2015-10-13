'use strict';

goog.provide('grrUi.user.module');

goog.require('grrUi.core.module');
goog.require('grrUi.forms.module');
goog.require('grrUi.user.userDashboardDirective.UserDashboardDirective');
goog.require('grrUi.user.userSettingsButtonDirective.UserSettingsButtonDirective');


/**
 * Angular module for user-related UI.
 */
grrUi.user.module = angular.module('grrUi.user', [grrUi.core.module.name,
                                                   grrUi.forms.module.name]);


grrUi.user.module.directive(
    grrUi.user.userDashboardDirective.UserDashboardDirective
        .directive_name,
    grrUi.user.userDashboardDirective.UserDashboardDirective);
grrUi.user.module.directive(
    grrUi.user.userSettingsButtonDirective.UserSettingsButtonDirective
        .directive_name,
    grrUi.user.userSettingsButtonDirective.UserSettingsButtonDirective);
