'use strict';

goog.provide('grrUi.user.module');

goog.require('grrUi.core.module');
goog.require('grrUi.forms.module');
goog.require('grrUi.user.userDashboardDirective.UserDashboardDirective');
goog.require('grrUi.user.userDesktopNotificationsDirective.UserDesktopNotificationsDirective');
goog.require('grrUi.user.userLabelDirective.UserLabelDirective');
goog.require('grrUi.user.userNotificationButtonDirective.UserNotificationButtonDirective');
goog.require('grrUi.user.userNotificationDialogDirective.UserNotificationDialogDirective');
goog.require('grrUi.user.userNotificationItemDirective.UserNotificationItemDirective');
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
grrUi.core.module.directive(
    grrUi.user.userDesktopNotificationsDirective.UserDesktopNotificationsDirective.directive_name,
    grrUi.user.userDesktopNotificationsDirective.UserDesktopNotificationsDirective);
grrUi.core.module.directive(
    grrUi.user.userLabelDirective.UserLabelDirective.directive_name,
    grrUi.user.userLabelDirective.UserLabelDirective);
grrUi.core.module.directive(
    grrUi.user.userNotificationButtonDirective.UserNotificationButtonDirective.directive_name,
    grrUi.user.userNotificationButtonDirective.UserNotificationButtonDirective);
grrUi.core.module.directive(
    grrUi.user.userNotificationDialogDirective.UserNotificationDialogDirective.directive_name,
    grrUi.user.userNotificationDialogDirective.UserNotificationDialogDirective);
grrUi.core.module.directive(
    grrUi.user.userNotificationItemDirective.UserNotificationItemDirective.directive_name,
    grrUi.user.userNotificationItemDirective.UserNotificationItemDirective);
grrUi.user.module.directive(
    grrUi.user.userSettingsButtonDirective.UserSettingsButtonDirective
        .directive_name,
    grrUi.user.userSettingsButtonDirective.UserSettingsButtonDirective);
