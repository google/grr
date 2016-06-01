goog.provide('grrUi.hunt.newHuntWizard.module');

goog.require('grrUi.core.module');

goog.require('grrUi.hunt.newHuntWizard.configureFlowPageDirective.ConfigureFlowPageDirective');
goog.require('grrUi.hunt.newHuntWizard.configureOutputPluginsPageDirective.ConfigureOutputPluginsPageDirective');
goog.require('grrUi.hunt.newHuntWizard.configureRulesPageDirective.ConfigureRulesPageDirective');
goog.require('grrUi.hunt.newHuntWizard.copyFormDirective.CopyFormDirective');
goog.require('grrUi.hunt.newHuntWizard.createHuntFromFlowFormDirective.CreateHuntFromFlowFormDirective');
goog.require('grrUi.hunt.newHuntWizard.formDirective.FormDirective');
goog.require('grrUi.hunt.newHuntWizard.reviewPageDirective.ReviewPageDirective');
goog.require('grrUi.hunt.newHuntWizard.statusPageDirective.StatusPageDirective');


/**
 * Angular module for new hunt wizard UI.
 */
grrUi.hunt.newHuntWizard.module = angular.module('grrUi.hunt.newHuntWizard',
                                   ['ui.bootstrap',
                                    grrUi.core.module.name]);

grrUi.hunt.newHuntWizard.module.directive(
    grrUi.hunt.newHuntWizard.configureFlowPageDirective
        .ConfigureFlowPageDirective.directive_name,
    grrUi.hunt.newHuntWizard.configureFlowPageDirective
        .ConfigureFlowPageDirective);
grrUi.hunt.newHuntWizard.module.directive(
    grrUi.hunt.newHuntWizard.configureOutputPluginsPageDirective
        .ConfigureOutputPluginsPageDirective.directive_name,
    grrUi.hunt.newHuntWizard.configureOutputPluginsPageDirective
        .ConfigureOutputPluginsPageDirective);
grrUi.hunt.newHuntWizard.module.directive(
    grrUi.hunt.newHuntWizard.configureRulesPageDirective
        .ConfigureRulesPageDirective.directive_name,
    grrUi.hunt.newHuntWizard.configureRulesPageDirective
        .ConfigureRulesPageDirective);
grrUi.hunt.newHuntWizard.module.directive(
    grrUi.hunt.newHuntWizard.reviewPageDirective.ReviewPageDirective
        .directive_name,
    grrUi.hunt.newHuntWizard.reviewPageDirective.ReviewPageDirective);
grrUi.hunt.newHuntWizard.module.directive(
    grrUi.hunt.newHuntWizard.statusPageDirective.StatusPageDirective
        .directive_name,
    grrUi.hunt.newHuntWizard.statusPageDirective.StatusPageDirective);

grrUi.hunt.newHuntWizard.module.directive(
    grrUi.hunt.newHuntWizard.copyFormDirective.CopyFormDirective.directive_name,
    grrUi.hunt.newHuntWizard.copyFormDirective.CopyFormDirective);
grrUi.hunt.newHuntWizard.module.directive(
    grrUi.hunt.newHuntWizard.formDirective.FormDirective.directive_name,
    grrUi.hunt.newHuntWizard.formDirective.FormDirective);
grrUi.hunt.newHuntWizard.module.directive(
    grrUi.hunt.newHuntWizard.createHuntFromFlowFormDirective
        .CreateHuntFromFlowFormDirective.directive_name,
    grrUi.hunt.newHuntWizard.createHuntFromFlowFormDirective
        .CreateHuntFromFlowFormDirective);
