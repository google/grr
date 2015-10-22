'use strict';

goog.provide('grrUi.forms.outputPluginDescriptorFormDirective.OutputPluginDescriptorFormController');
goog.provide('grrUi.forms.outputPluginDescriptorFormDirective.OutputPluginDescriptorFormDirective');


goog.scope(function() {

/**
 * Controller for OutputPluginDescriptorFormDirective.
 *
 * @constructor
 * @param {!angular.Scope} $scope
 * @param {!grrUi.core.apiService.ApiService} grrApiService
 * @param {!grrUi.core.reflectionService.ReflectionService} grrReflectionService
 * @ngInject
 */
grrUi.forms.outputPluginDescriptorFormDirective
    .OutputPluginDescriptorFormController = function(
        $scope, grrApiService, grrReflectionService) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @private {!grrUi.core.apiService.ApiService} */
  this.grrApiService_ = grrApiService;

  /** @private {!grrUi.core.reflectionService.ReflectionService} */
  this.grrReflectionService_ = grrReflectionService;

  /** @type {Object} */
  this.outputPluginsDescriptors;

  /** @type {Array<string>} */
  this.allowedPluginsNames;

  this.grrApiService_.get('/output-plugins/all').then(function(response) {
    this.outputPluginsDescriptors = response['data'];
    this.allowedPluginsNames = Object.keys(
        /** @type {!Object} */ (this.outputPluginsDescriptors)).sort();

    if (angular.isUndefined(
        this.scope_.$eval('value.value.plugin_name.value'))) {
      this.scope_['value']['value']['plugin_name'] = {
        type: 'RDFString',
        value: this.allowedPluginsNames[0]
      };
    }

    this.scope_.$watch('value.value.plugin_name.value', function(newValue) {
      if (angular.isDefined(newValue)) {
        var argsType = this.outputPluginsDescriptors[newValue]['args_type'];

        var pluginArgs = this.scope_['value']['value']['plugin_args'];
        // We want to replace the plugin args only if they're undefined or
        // their type differs from the selected ones. This check helps
        // prefilled forms to keep prefilled data.
        if (angular.isUndefined(pluginArgs) ||
            pluginArgs['type'] != argsType) {
          this.grrReflectionService_.getRDFValueDescriptor(argsType).then(
              function(descriptor) {
                this.scope_['value']['value']['plugin_args'] =
                    angular.copy(descriptor['default']);
              }.bind(this));
        }
      }
    }.bind(this));
  }.bind(this));
};
var OutputPluginDescriptorFormController =
    grrUi.forms.outputPluginDescriptorFormDirective
    .OutputPluginDescriptorFormController;

/**
 * OutputPluginDescriptorFormDirective definition.
 *
 * @return {angular.Directive} Directive definition object.
 */
grrUi.forms.outputPluginDescriptorFormDirective
    .OutputPluginDescriptorFormDirective = function() {
  return {
    restrict: 'E',
    scope: {
      value: '='
    },
    templateUrl: '/static/angular-components/forms/' +
        'output-plugin-descriptor-form.html',
    controller: OutputPluginDescriptorFormController,
    controllerAs: 'controller'
  };
};


/**
 * Directive's name in Angular.
 *
 * @const
 * @export
 */
grrUi.forms.outputPluginDescriptorFormDirective
    .OutputPluginDescriptorFormDirective
    .directive_name = 'grrOutputPluginDescriptorForm';


/**
 * Semantic type corresponding to this directive.
 *
 * @const
 * @export
 */
grrUi.forms.outputPluginDescriptorFormDirective
    .OutputPluginDescriptorFormDirective
    .semantic_type = 'OutputPluginDescriptor';


});  // goog.scope
