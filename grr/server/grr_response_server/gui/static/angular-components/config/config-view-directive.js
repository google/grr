'use strict';

goog.module('grrUi.config.configViewDirective');
goog.module.declareLegacyNamespace();



/**
 * Controller for ConfigViewDirective.
 *
 * @constructor
 * @param {!angular.Scope} $scope
 * @param {!angular.$http} $http Angular HTTP service.
 * @ngInject
 */
const ConfigViewController = function($scope, $http) {
  $http.get('/api/config').then(function(config) {
    this.items = {};

    angular.forEach(config['data']['sections'], function(section) {
      var sectionName = section['value']['name']['value'];
      var sectionOptions = section['value']['options'];

      this.items[sectionName] = {};
      angular.forEach(sectionOptions, function(option) {
        this.items[sectionName][option['value']['name']['value']] = option;
      }.bind(this));
    }.bind(this));
  }.bind(this));
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
