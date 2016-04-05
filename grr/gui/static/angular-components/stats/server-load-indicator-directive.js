'use strict';

goog.provide('grrUi.stats.serverLoadIndicatorDirective.ServerLoadIndicatorController');
goog.provide('grrUi.stats.serverLoadIndicatorDirective.ServerLoadIndicatorDirective');

goog.scope(function() {



/**
 * Controller for ServerLoadIndicatorDirective.
 *
 * @constructor
 * @param {!angular.Scope} $scope
 * @ngInject
 */
grrUi.stats.serverLoadIndicatorDirective.ServerLoadIndicatorController =
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

var ServerLoadIndicatorController = grrUi.stats.serverLoadIndicatorDirective.
    ServerLoadIndicatorController;



/**
 * Directive for displaying a health indicator.
 *
 * @constructor
 * @ngInject
 * @export
 */
grrUi.stats.serverLoadIndicatorDirective.ServerLoadIndicatorDirective =
    function() {
      return {
        scope: {
          status: '='
        },
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
grrUi.stats.serverLoadIndicatorDirective.
    ServerLoadIndicatorDirective.directive_name = 'grrServerLoadIndicator';

});  // goog.scope
