'use strict';

goog.module('grrUi.hunt.newHuntWizard.newHuntWizard');
goog.module.declareLegacyNamespace();

const {ConfigureFlowPageDirective} = goog.require('grrUi.hunt.newHuntWizard.configureFlowPageDirective');
const {ConfigureHuntPageDirective} = goog.require('grrUi.hunt.newHuntWizard.configureHuntPageDirective');
const {ConfigureOutputPluginsPageDirective} = goog.require('grrUi.hunt.newHuntWizard.configureOutputPluginsPageDirective');
const {ConfigureRulesPageDirective} = goog.require('grrUi.hunt.newHuntWizard.configureRulesPageDirective');
const {CopyFormDirective} = goog.require('grrUi.hunt.newHuntWizard.copyFormDirective');
const {CreateHuntFromFlowFormDirective} = goog.require('grrUi.hunt.newHuntWizard.createHuntFromFlowFormDirective');
const {FormDirective} = goog.require('grrUi.hunt.newHuntWizard.formDirective');
const {ReviewPageDirective} = goog.require('grrUi.hunt.newHuntWizard.reviewPageDirective');
const {StatusPageDirective} = goog.require('grrUi.hunt.newHuntWizard.statusPageDirective');
const {coreModule} = goog.require('grrUi.core.core');


/**
 * Angular module for new hunt wizard UI.
 */
exports.newHuntWizardModule = angular.module(
    'grrUi.hunt.newHuntWizard', ['ui.bootstrap', coreModule.name]);

exports.newHuntWizardModule.directive(
    ConfigureFlowPageDirective.directive_name, ConfigureFlowPageDirective);
exports.newHuntWizardModule.directive(
    ConfigureHuntPageDirective.directive_name, ConfigureHuntPageDirective);
exports.newHuntWizardModule.directive(
    ConfigureOutputPluginsPageDirective.directive_name,
    ConfigureOutputPluginsPageDirective);
exports.newHuntWizardModule.directive(
    ConfigureRulesPageDirective.directive_name, ConfigureRulesPageDirective);
exports.newHuntWizardModule.directive(
    ReviewPageDirective.directive_name, ReviewPageDirective);
exports.newHuntWizardModule.directive(
    StatusPageDirective.directive_name, StatusPageDirective);

exports.newHuntWizardModule.directive(
    CopyFormDirective.directive_name, CopyFormDirective);
exports.newHuntWizardModule.directive(
    FormDirective.directive_name, FormDirective);
exports.newHuntWizardModule.directive(
    CreateHuntFromFlowFormDirective.directive_name,
    CreateHuntFromFlowFormDirective);
