'use strict';

goog.provide('grrUi.hunt.newHuntWizard.configureOutputPluginsPageDirective.ConfigureOutputPluginsPageController');
goog.provide('grrUi.hunt.newHuntWizard.configureOutputPluginsPageDirective.ConfigureOutputPluginsPageDirective');

goog.scope(function() {

/**
 * Controller for ConfigureOutputPluginsPageDirective.
 *
 * @param {!angular.Scope} $scope
 * @param {!grrUi.core.reflectionService.ReflectionService} grrReflectionService
 * @constructor
 * @ngInject
 */
grrUi.hunt.newHuntWizard.configureOutputPluginsPageDirective
    .ConfigureOutputPluginsPageController = function(
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
var ConfigureOutputPluginsPageController =
    grrUi.hunt.newHuntWizard.configureOutputPluginsPageDirective
    .ConfigureOutputPluginsPageController;


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
 * @constructor
 * @ngInject
 * @export
 */
grrUi.hunt.newHuntWizard.configureOutputPluginsPageDirective
    .ConfigureOutputPluginsPageDirective = function() {
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
grrUi.hunt.newHuntWizard.configureOutputPluginsPageDirective
    .ConfigureOutputPluginsPageDirective
    .directive_name = 'grrConfigureOutputPluginsPage';

});  // goog.scope
