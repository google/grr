'use strict';

goog.module('grrUi.hunt.newHuntWizard.configureOutputPluginsPageDirective');
goog.module.declareLegacyNamespace();



/**
 * Controller for ConfigureOutputPluginsPageDirective.
 *
 * @param {!angular.Scope} $scope
 * @param {!grrUi.core.reflectionService.ReflectionService} grrReflectionService
 * @constructor
 * @ngInject
 */
const ConfigureOutputPluginsPageController = function(
        $scope, grrReflectionService) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @private {!grrUi.core.reflectionService.ReflectionService} */
  this.grrReflectionService_ = grrReflectionService;

  /** @type {Object} */
  this.outputPluginsField;

  /** @type {Object} */
  this.outputPluginDescriptor;

  this.grrReflectionService_.getRDFValueDescriptor(
      'GenericHuntArgs', true).then(this.onDescriptors_.bind(this));
};


/**
 * Handles response of GenericHuntArgs rdfvalue descriptors request.
 *
 * @param {Object<string, Object>} descriptors Dictionary with GenericHuntArgs
 *     descriptor and all dependent descriptors.
 * @private
 */
ConfigureOutputPluginsPageController.prototype.onDescriptors_ = function(
    descriptors) {
  angular.forEach(descriptors['GenericHuntArgs']['fields'], function(field) {
    if (field.name == 'output_plugins') {
      this.outputPluginsField = field;
    }
  }.bind(this));
  this.outputPluginDescriptor = descriptors['OutputPluginDescriptor'];
};

/**
 * Directive for showing wizard-like forms with multiple named steps/pages.
 *
 * @return {!angular.Directive} Directive definition object.
 * @ngInject
 * @export
 */
exports.ConfigureOutputPluginsPageDirective = function() {
  return {
    scope: {
      outputPlugins: '=',
    },
    restrict: 'E',
    templateUrl: '/static/angular-components/hunt/new-hunt-wizard/' +
        'configure-output-plugins-page.html',
    controller: ConfigureOutputPluginsPageController,
    controllerAs: 'controller'
  };
};


/**
 * Directive's name in Angular.
 *
 * @const
 * @export
 */
exports.ConfigureOutputPluginsPageDirective.directive_name =
    'grrConfigureOutputPluginsPage';
