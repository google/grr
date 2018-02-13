goog.provide('grrUi.hunt.newHuntWizard.newHuntWizard');
goog.provide('grrUi.hunt.newHuntWizard.newHuntWizard.newHuntWizardModule');

goog.require('grrUi.core.core');  // USE: coreModule

goog.require('grrUi.hunt.newHuntWizard.configureFlowPageDirective');  // USE: ConfigureFlowPageDirective
goog.require('grrUi.hunt.newHuntWizard.configureHuntPageDirective');  // USE: ConfigureHuntPageDirective
goog.require('grrUi.hunt.newHuntWizard.configureOutputPluginsPageDirective');  // USE: ConfigureOutputPluginsPageDirective
goog.require('grrUi.hunt.newHuntWizard.configureRulesPageDirective');  // USE: ConfigureRulesPageDirective
goog.require('grrUi.hunt.newHuntWizard.copyFormDirective');  // USE: CopyFormDirective
goog.require('grrUi.hunt.newHuntWizard.createHuntFromFlowFormDirective');  // USE: CreateHuntFromFlowFormDirective
goog.require('grrUi.hunt.newHuntWizard.formDirective');  // USE: FormDirective
goog.require('grrUi.hunt.newHuntWizard.reviewPageDirective');  // USE: ReviewPageDirective
goog.require('grrUi.hunt.newHuntWizard.statusPageDirective');  // USE: StatusPageDirective


/**
 * Angular module for new hunt wizard UI.
 */
grrUi.hunt.newHuntWizard.newHuntWizard.newHuntWizardModule = angular.module(
    'grrUi.hunt.newHuntWizard',
    ['ui.bootstrap', grrUi.core.core.coreModule.name]);

grrUi.hunt.newHuntWizard.newHuntWizard.newHuntWizardModule.directive(
    grrUi.hunt.newHuntWizard.configureFlowPageDirective
        .ConfigureFlowPageDirective.directive_name,
    grrUi.hunt.newHuntWizard.configureFlowPageDirective
        .ConfigureFlowPageDirective);
grrUi.hunt.newHuntWizard.newHuntWizard.newHuntWizardModule.directive(
    grrUi.hunt.newHuntWizard.configureHuntPageDirective
        .ConfigureHuntPageDirective.directive_name,
    grrUi.hunt.newHuntWizard.configureHuntPageDirective
        .ConfigureHuntPageDirective);
grrUi.hunt.newHuntWizard.newHuntWizard.newHuntWizardModule.directive(
    grrUi.hunt.newHuntWizard.configureOutputPluginsPageDirective
        .ConfigureOutputPluginsPageDirective.directive_name,
    grrUi.hunt.newHuntWizard.configureOutputPluginsPageDirective
        .ConfigureOutputPluginsPageDirective);
grrUi.hunt.newHuntWizard.newHuntWizard.newHuntWizardModule.directive(
    grrUi.hunt.newHuntWizard.configureRulesPageDirective
        .ConfigureRulesPageDirective.directive_name,
    grrUi.hunt.newHuntWizard.configureRulesPageDirective
        .ConfigureRulesPageDirective);
grrUi.hunt.newHuntWizard.newHuntWizard.newHuntWizardModule.directive(
    grrUi.hunt.newHuntWizard.reviewPageDirective.ReviewPageDirective
        .directive_name,
    grrUi.hunt.newHuntWizard.reviewPageDirective.ReviewPageDirective);
grrUi.hunt.newHuntWizard.newHuntWizard.newHuntWizardModule.directive(
    grrUi.hunt.newHuntWizard.statusPageDirective.StatusPageDirective
        .directive_name,
    grrUi.hunt.newHuntWizard.statusPageDirective.StatusPageDirective);

grrUi.hunt.newHuntWizard.newHuntWizard.newHuntWizardModule.directive(
    grrUi.hunt.newHuntWizard.copyFormDirective.CopyFormDirective.directive_name,
    grrUi.hunt.newHuntWizard.copyFormDirective.CopyFormDirective);
grrUi.hunt.newHuntWizard.newHuntWizard.newHuntWizardModule.directive(
    grrUi.hunt.newHuntWizard.formDirective.FormDirective.directive_name,
    grrUi.hunt.newHuntWizard.formDirective.FormDirective);
grrUi.hunt.newHuntWizard.newHuntWizard.newHuntWizardModule.directive(
    grrUi.hunt.newHuntWizard.createHuntFromFlowFormDirective
        .CreateHuntFromFlowFormDirective.directive_name,
    grrUi.hunt.newHuntWizard.createHuntFromFlowFormDirective
        .CreateHuntFromFlowFormDirective);
