'use strict';

goog.module('grrUi.stats.serverLoadIndicatorDirective');
goog.module.declareLegacyNamespace();



/**
 * Controller for ServerLoadIndicatorDirective.
 *
 * @constructor
 * @param {!angular.Scope} $scope
 * @ngInject
 */
const ServerLoadIndicatorController =
    function($scope) {
      /** @private {!angular.Scope} */
      this.scope_ = $scope;

      /** @export {string} */
      this.imageFile;

      /** @private {Object.<string, string>} */
      this.files_ = {
        normal: 'online.png',
        warning: 'online-1d.png',
        danger: 'offline.png',
        unknown: 'unknown-indicator.png'
      };

      this.scope_.$watch('status', function(newValue) {
        if (angular.isDefined(newValue) && newValue !== 'normal' &&
            newValue !== 'warning' && newValue !== 'danger' &&
            newValue !== 'unknown') {
          throw new Error('status can be undefined or "normal", ' +
              '"danger", "warning" or "unknown".');
        }

        if (angular.isUndefined(newValue)) {
          this.imageFile = this.files_['unknown'];
        } else {
          this.imageFile = this.files_[newValue];
        }
      }.bind(this));
    };




/**
 * Directive for displaying a health indicator.
 *
 * @return {!angular.Directive} Directive definition object.
 * @ngInject
 * @export
 */
exports.ServerLoadIndicatorDirective = function() {
  return {
    scope: {status: '='},
    restrict: 'E',
    templateUrl: '/static/angular-components/stats/' +
        'server-load-indicator.html',
    controller: ServerLoadIndicatorController,
    controllerAs: 'controller'
  };
};


/**
 * Name of the directive as registered in Angular.
 *
 * @const
 * @export
 */
exports.ServerLoadIndicatorDirective.directive_name = 'grrServerLoadIndicator';
