goog.module('grrUi.config.configViewDirective');
goog.module.declareLegacyNamespace();



/**
 * Controller for ConfigViewDirective.
 * @unrestricted
 */
const ConfigViewController = class {
  /**
   * @param {!angular.Scope} $scope
   * @param {!angular.$http} $http Angular HTTP service.
   * @ngInject
   */
  constructor($scope, $http) {
    $http.get('/api/config').then(function(config) {
      this.items = {};

      angular.forEach(config['data']['sections'], function(section) {
        const sectionName = section['value']['name']['value'];
        const sectionOptions = section['value']['options'];

        this.items[sectionName] = {};
        angular.forEach(sectionOptions, function(option) {
          this.items[sectionName][option['value']['name']['value']] = option;
        }.bind(this));
      }.bind(this));
    }.bind(this));
  }
};


/**
 * ConfigViewDirective definition.
 * @return {angular.Directive} Directive definition object.
 */
exports.ConfigViewDirective = function() {
  return {
    restrict: 'E',
    scope: {},
    templateUrl: '/static/angular-components/config/config-view.html',
    controller: ConfigViewController,
    controllerAs: 'controller'
  };
};


/**
 * Name of the directive in Angular.
 *
 * @const
 * @export
 */
exports.ConfigViewDirective.directive_name = 'grrConfigView';
