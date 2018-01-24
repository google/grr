goog.provide('grrUi.hunt.newHuntWizard.newHuntWizardModule');

goog.require('grrUi.core.coreModule');

goog.require('grrUi.hunt.newHuntWizard.configureFlowPageDirective.ConfigureFlowPageDirective');
goog.require('grrUi.hunt.newHuntWizard.configureHuntPageDirective.ConfigureHuntPageDirective');
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
grrUi.hunt.newHuntWizard.newHuntWizardModule = angular.module('grrUi.hunt.newHuntWizard',
                                   ['ui.bootstrap',
                                    grrUi.core.coreModule.name]);

grrUi.hunt.newHuntWizard.newHuntWizardModule.directive(
    grrUi.hunt.newHuntWizard.configureFlowPageDirective
        .ConfigureFlowPageDirective.directive_name,
    grrUi.hunt.newHuntWizard.configureFlowPageDirective
        .ConfigureFlowPageDirective);
grrUi.hunt.newHuntWizard.newHuntWizardModule.directive(
    grrUi.hunt.newHuntWizard.configureHuntPageDirective
        .ConfigureHuntPageDirective.directive_name,
    grrUi.hunt.newHuntWizard.configureHuntPageDirective
        .ConfigureHuntPageDirective);
grrUi.hunt.newHuntWizard.newHuntWizardModule.directive(
    grrUi.hunt.newHuntWizard.configureOutputPluginsPageDirective
        .ConfigureOutputPluginsPageDirective.directive_name,
    grrUi.hunt.newHuntWizard.configureOutputPluginsPageDirective
        .ConfigureOutputPluginsPageDirective);
grrUi.hunt.newHuntWizard.newHuntWizardModule.directive(
    grrUi.hunt.newHuntWizard.configureRulesPageDirective
        .ConfigureRulesPageDirective.directive_name,
    grrUi.hunt.newHuntWizard.configureRulesPageDirective
        .ConfigureRulesPageDirective);
grrUi.hunt.newHuntWizard.newHuntWizardModule.directive(
    grrUi.hunt.newHuntWizard.reviewPageDirective.ReviewPageDirective
        .directive_name,
    grrUi.hunt.newHuntWizard.reviewPageDirective.ReviewPageDirective);
grrUi.hunt.newHuntWizard.newHuntWizardModule.directive(
    grrUi.hunt.newHuntWizard.statusPageDirective.StatusPageDirective
        .directive_name,
    grrUi.hunt.newHuntWizard.statusPageDirective.StatusPageDirective);

grrUi.hunt.newHuntWizard.newHuntWizardModule.directive(
    grrUi.hunt.newHuntWizard.copyFormDirective.CopyFormDirective.directive_name,
    grrUi.hunt.newHuntWizard.copyFormDirective.CopyFormDirective);
grrUi.hunt.newHuntWizard.newHuntWizardModule.directive(
    grrUi.hunt.newHuntWizard.formDirective.FormDirective.directive_name,
    grrUi.hunt.newHuntWizard.formDirective.FormDirective);
grrUi.hunt.newHuntWizard.newHuntWizardModule.directive(
    grrUi.hunt.newHuntWizard.createHuntFromFlowFormDirective
        .CreateHuntFromFlowFormDirective.directive_name,
    grrUi.hunt.newHuntWizard.createHuntFromFlowFormDirective
        .CreateHuntFromFlowFormDirective);
