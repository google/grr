'use strict';

goog.provide('grrUi.user');
goog.provide('grrUi.user.userModule');

goog.require('grrUi.core');                         // USE: coreModule
goog.require('grrUi.forms');                        // USE: formsModule
goog.require('grrUi.user.userDashboardDirective');  // USE: UserDashboardDirective
goog.require('grrUi.user.userDesktopNotificationsDirective');  // USE: UserDesktopNotificationsDirective
goog.require('grrUi.user.userLabelDirective');  // USE: UserLabelDirective
goog.require('grrUi.user.userNotificationButtonDirective');  // USE: UserNotificationButtonDirective
goog.require('grrUi.user.userNotificationDialogDirective');  // USE: UserNotificationDialogDirective
goog.require('grrUi.user.userNotificationItemDirective');  // USE: UserNotificationItemDirective
goog.require('grrUi.user.userSettingsButtonDirective');  // USE: UserSettingsButtonDirective


/**
 * Angular module for user-related UI.
 */
grrUi.user.userModule = angular.module('grrUi.user', [grrUi.core.coreModule.name,
                                                  grrUi.forms.formsModule.name]);


grrUi.user.userModule.directive(
    grrUi.user.userDashboardDirective.UserDashboardDirective
        .directive_name,
    grrUi.user.userDashboardDirective.UserDashboardDirective);
grrUi.user.userModule.directive(
    grrUi.user.userDesktopNotificationsDirective
        .UserDesktopNotificationsDirective.directive_name,
    grrUi.user.userDesktopNotificationsDirective
        .UserDesktopNotificationsDirective);
grrUi.user.userModule.directive(
    grrUi.user.userLabelDirective.UserLabelDirective.directive_name,
    grrUi.user.userLabelDirective.UserLabelDirective);
grrUi.user.userModule.directive(
    grrUi.user.userNotificationButtonDirective.UserNotificationButtonDirective
        .directive_name,
    grrUi.user.userNotificationButtonDirective.UserNotificationButtonDirective);
grrUi.user.userModule.directive(
    grrUi.user.userNotificationDialogDirective.UserNotificationDialogDirective
        .directive_name,
    grrUi.user.userNotificationDialogDirective.UserNotificationDialogDirective);
grrUi.user.userModule.directive(
    grrUi.user.userNotificationItemDirective.UserNotificationItemDirective
        .directive_name,
    grrUi.user.userNotificationItemDirective.UserNotificationItemDirective);
grrUi.user.userModule.directive(
    grrUi.user.userSettingsButtonDirective.UserSettingsButtonDirective
        .directive_name,
    grrUi.user.userSettingsButtonDirective.UserSettingsButtonDirective);
