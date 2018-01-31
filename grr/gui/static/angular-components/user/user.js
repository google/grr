'use strict';

goog.provide('grrUi.user');
goog.provide('grrUi.user.userModule');

goog.require('grrUi.core.coreModule');
goog.require('grrUi.forms.formsModule');
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
grrUi.user.userModule = angular.module('grrUi.user', [grrUi.core.coreModule.name,
                                                  grrUi.forms.formsModule.name]);


grrUi.user.userModule.directive(
    grrUi.user.userDashboardDirective.UserDashboardDirective
        .directive_name,
    grrUi.user.userDashboardDirective.UserDashboardDirective);
grrUi.core.coreModule.directive(
    grrUi.user.userDesktopNotificationsDirective.UserDesktopNotificationsDirective.directive_name,
    grrUi.user.userDesktopNotificationsDirective.UserDesktopNotificationsDirective);
grrUi.core.coreModule.directive(
    grrUi.user.userLabelDirective.UserLabelDirective.directive_name,
    grrUi.user.userLabelDirective.UserLabelDirective);
grrUi.core.coreModule.directive(
    grrUi.user.userNotificationButtonDirective.UserNotificationButtonDirective.directive_name,
    grrUi.user.userNotificationButtonDirective.UserNotificationButtonDirective);
grrUi.core.coreModule.directive(
    grrUi.user.userNotificationDialogDirective.UserNotificationDialogDirective.directive_name,
    grrUi.user.userNotificationDialogDirective.UserNotificationDialogDirective);
grrUi.core.coreModule.directive(
    grrUi.user.userNotificationItemDirective.UserNotificationItemDirective.directive_name,
    grrUi.user.userNotificationItemDirective.UserNotificationItemDirective);
grrUi.user.userModule.directive(
    grrUi.user.userSettingsButtonDirective.UserSettingsButtonDirective
        .directive_name,
    grrUi.user.userSettingsButtonDirective.UserSettingsButtonDirective);
