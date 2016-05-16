'use strict';

goog.provide('grrUi.sidebar.module');
goog.require('grrUi.sidebar.clientSummaryDirective.ClientSummaryDirective');
goog.require('grrUi.sidebar.navDropdownDirective.NavDropdownDirective');
goog.require('grrUi.sidebar.navLinkDirective.NavLinkDirective');
goog.require('grrUi.sidebar.navigatorDirective.NavigatorDirective');

/**
 * Angular module for layout-related UI.
 */
grrUi.sidebar.module = angular.module('grrUi.sidebar', []);

grrUi.sidebar.module.directive(
    grrUi.sidebar.clientSummaryDirective.ClientSummaryDirective.directive_name,
    grrUi.sidebar.clientSummaryDirective.ClientSummaryDirective);
grrUi.sidebar.module.directive(
    grrUi.sidebar.navDropdownDirective.NavDropdownDirective.directive_name,
    grrUi.sidebar.navDropdownDirective.NavDropdownDirective);
grrUi.sidebar.module.directive(
    grrUi.sidebar.navLinkDirective.NavLinkDirective.directive_name,
    grrUi.sidebar.navLinkDirective.NavLinkDirective);
grrUi.sidebar.module.directive(
    grrUi.sidebar.navigatorDirective.NavigatorDirective.directive_name,
    grrUi.sidebar.navigatorDirective.NavigatorDirective);