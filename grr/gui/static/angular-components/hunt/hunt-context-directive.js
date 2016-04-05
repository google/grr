'use strict';

goog.provide('grrUi.hunt.huntContextDirective.HuntContextController');
goog.provide('grrUi.hunt.huntContextDirective.HuntContextDirective');

goog.scope(function() {


/**
 * Controller for HuntContextDirective.
 *
 * @constructor
 * @param {!angular.Scope} $scope
 * @param {!grrUi.core.apiService.ApiService} grrApiService
 * @ngInject
 */
grrUi.hunt.huntContextDirective.HuntContextController = function(
    $scope, grrApiService) {

  /** @private {!grrUi.core.apiService.ApiService} */
  this.grrApiService_ = grrApiService;

  /** @export {Object} */
  this.context;

  $scope.$watch('huntUrn', this.onHuntUrnChange_.bind(this));
};

var HuntContextController =
    grrUi.hunt.huntContextDirective.HuntContextController;


/**
 * Handles huntUrn attribute changes.
 *
 * @param {?string} huntUrn
 * @private
 */
HuntContextController.prototype.onHuntUrnChange_ = function(huntUrn) {
  if (!angular.isString(huntUrn)) {
    return;
  }

  var components = huntUrn.split('/');
  var huntId = components[components.length - 1];
  var url = '/hunts/' + huntId + '/context';
  this.grrApiService_.get(url).then(function success(response) {
    this.context = response.data['context'];
  }.bind(this));
};


/**
 * Directive for displaying the hunt context of a hunt with a given URN.
 *
 * @constructor
 * @ngInject
 * @export
 */
grrUi.hunt.huntContextDirective.HuntContextDirective = function() {
  return {
    scope: {
      huntUrn: '='
    },
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
grrUi.hunt.huntContextDirective.HuntContextDirective.directive_name =
    'grrHuntContext';

});  // goog.scope
