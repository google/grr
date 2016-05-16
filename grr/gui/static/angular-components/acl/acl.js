goog.provide('grrUi.acl.module');
goog.require('grrUi.acl.grantAccessDirective.GrantAccessDirective');

/**
 * Angular module for acl GRR UI components.
 */
grrUi.acl.module = angular.module('grrUi.acl', []);

grrUi.acl.module.directive(
    grrUi.acl.grantAccessDirective.GrantAccessDirective.directive_name,
    grrUi.acl.grantAccessDirective.GrantAccessDirective);