goog.module('grrUi.forms.outputPluginDescriptorFormDirective');
goog.module.declareLegacyNamespace();

const apiService = goog.requireType('grrUi.core.apiService');
const reflectionService = goog.requireType('grrUi.core.reflectionService');



/**
 * Controller for OutputPluginDescriptorFormDirective.
 * @unrestricted
 */
const OutputPluginDescriptorFormController = class {
  /**
   * @param {!angular.Scope} $scope
   * @param {!apiService.ApiService} grrApiService
   * @param {!reflectionService.ReflectionService}
   *     grrReflectionService
   * @ngInject
   */
  constructor($scope, grrApiService, grrReflectionService) {
    /** @private {!angular.Scope} */
    this.scope_ = $scope;

    /** @private {!apiService.ApiService} */
    this.grrApiService_ = grrApiService;

    /** @private {!reflectionService.ReflectionService} */
    this.grrReflectionService_ = grrReflectionService;

    /** @type {Object} */
    this.outputPluginsDescriptors;

    /** @type {Array<string>} */
    this.allowedPluginsNames;

    this.grrApiService_.get('/output-plugins/all').then(function(response) {
      this.outputPluginsDescriptors = {};

      angular.forEach(response['data']['items'], function(item) {
        if (item['plugin_type'] === 'LEGACY') {
          this.outputPluginsDescriptors[item['name']] = item;
        }
      }.bind(this));

      this.allowedPluginsNames =
          Object
              .keys(
                  /** @type {!Object} */ (this.outputPluginsDescriptors))
              .sort();

      if (angular.isUndefined(
              this.scope_.$eval('value.value.plugin_name.value'))) {
        this.scope_['value']['value']['plugin_name'] = {
          type: 'RDFString',
          value: this.allowedPluginsNames[0]
        };
      }

      this.scope_.$watch('value.value.plugin_name.value', function(newValue) {
        if (angular.isDefined(newValue)) {
          const argsType = this.outputPluginsDescriptors[newValue]['args_type'];

          // Prefer reading `args` and fallback to `plugin_args`
          const pluginArgs = this.scope_['value']['value']['args'] ||
              this.scope_['value']['value']['plugin_args'];

          // We want to replace the plugin args only if they're undefined or
          // their type differs from the selected ones. This check helps
          // prefilled forms to keep prefilled data.
          if (angular.isUndefined(pluginArgs) ||
              pluginArgs['type'] != argsType) {
            this.grrReflectionService_.getRDFValueDescriptor(argsType).then(
                function(descriptor) {
                  this.scope_['value']['value']['args'] =
                      angular.copy(descriptor['default']);
                }.bind(this));
          }
        }
      }.bind(this));
    }.bind(this));
  }
};

/**
 * OutputPluginDescriptorFormDirective definition.
 *
 * @return {angular.Directive} Directive definition object.
 */
exports.OutputPluginDescriptorFormDirective = function() {
  return {
    restrict: 'E',
    scope: {value: '='},
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
exports.OutputPluginDescriptorFormDirective.directive_name =
    'grrOutputPluginDescriptorForm';


/**
 * Semantic type corresponding to this directive.
 *
 * @const
 * @export
 */
exports.OutputPluginDescriptorFormDirective.semantic_type =
    'OutputPluginDescriptor';
