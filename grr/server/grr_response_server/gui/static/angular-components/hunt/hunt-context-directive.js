goog.module('grrUi.hunt.huntContextDirective');
goog.module.declareLegacyNamespace();

const apiService = goog.requireType('grrUi.core.apiService');



/**
 * Controller for HuntContextDirective.
 * @unrestricted
 */
const HuntContextController = class {
  /**
   * @param {!angular.Scope} $scope
   * @param {!apiService.ApiService} grrApiService
   * @ngInject
   */
  constructor($scope, grrApiService) {
    /** @private {!apiService.ApiService} */
    this.grrApiService_ = grrApiService;

    /** @export {Object} */
    this.context;
    /** @export {Object} */
    this.state;

    $scope.$watch('huntId', this.onHuntIdChange_.bind(this));
  }

  /**
   * Handles huntId attribute changes.
   *
   * @param {?string} huntId
   * @private
   */
  onHuntIdChange_(huntId) {
    if (!angular.isString(huntId)) {
      return;
    }

    var url = '/hunts/' + huntId + '/context';
    this.grrApiService_.get(url).then(function success(response) {
      this.context = response.data['context'];
      this.state = response.data['state'];
    }.bind(this));
  }
};



/**
 * Directive for displaying the hunt context of a hunt with a given URN.
 *
 * @return {!angular.Directive} Directive definition object.
 * @ngInject
 * @export
 */
exports.HuntContextDirective = function() {
  return {
    scope: {huntId: '='},
    restrict: 'E',
    templateUrl: '/static/angular-components/hunt/hunt-context.html',
    controller: HuntContextController,
    controllerAs: 'controller'
  };
};


/**
 * Directive's name in Angular.
 *
 * @const
 * @export
 */
exports.HuntContextDirective.directive_name = 'grrHuntContext';
