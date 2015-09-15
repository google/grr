'use strict';

goog.provide('grrUi.client.clientSearchBoxDirective.ClientSearchBoxController');
goog.provide('grrUi.client.clientSearchBoxDirective.ClientSearchBoxDirective');


goog.scope(function() {



/**
 * Controller for ClientSearchBoxDirective.
 *
 * @constructor
 * @param {!angular.Scope} $scope
 * @param {!angular.JQLite} $element
 * @param {!angular.$interval} $interval
 * @param {!grrUi.core.apiService.ApiService} grrApiService
 * @ngInject
 */
grrUi.client.clientSearchBoxDirective.ClientSearchBoxController = function(
    $scope, $element, $interval, grrApiService) {

  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @private {!angular.JQLite} */
  this.element_ = $element;

  /** @private {!angular.$interval} */
  this.interval_ = $interval;

  /** @private {!grrUi.core.apiService.ApiService} */
  this.grrApiService_ = grrApiService;

  /** @export {string} */
  this.query = '';

  // TODO(user): refactor completer into proper Angular directive.
  this.grrApiService_.get('/clients/labels').then(this.onGetLabels_.bind(this));
};

var ClientSearchBoxController =
    grrUi.client.clientSearchBoxDirective.ClientSearchBoxController;


/**
 * Handles /clients/labels response.
 *
 * @param {!Object} response
 * @private
 */
ClientSearchBoxController.prototype.onGetLabels_ = function(response) {
  var labels = {};
  angular.forEach(response['data']['labels'], function(label) {
    labels[label['value']['name']['value']] = 'X';
  });

  var intervalPromise = this.interval_(function() {
    var inputBox = $(this.element_).find('[name=q]');
    if (inputBox) {
      // TODO(user): convert completer into a proper Angular directive.
      grr.labels_completer.Completer(inputBox, Object.keys(labels), /label:/);

      if (grr.hash.main == 'HostTable' && grr.hash.q) {
        this.query = grr.hash.q;
        grr.layout('HostTable', 'main', {q: grr.hash.q});
      } else {
        inputBox.focus();
      }

      this.interval_.cancel(intervalPromise);
    }
  }.bind(this), 500, 10);
};


/**
 * Updates GRR UI with current query value (using legacy API).
 *
 * @export
 */
ClientSearchBoxController.prototype.submitQuery = function() {
  var sha_regex = /^[A-F0-9]{64}$/i;

  if (sha_regex.test(this.query)) {
    grr.layout('FilestoreTable', 'main', {q: this.query});
  } else {
    grr.publish('hash_state', 'main', 'HostTable');
    grr.publish('hash_state', 'q', this.query);
    grr.layout('HostTable', 'main', {q: this.query});
  }
};


/**
 * @export {string}
 * @const
 */
ClientSearchBoxController.prototype.contextHelpUrl =
    'user_manual.html#searching-for-a-client';


/**
 * Displays a table of clients.
 *
 * @return {angular.Directive} Directive definition object.
 */
grrUi.client.clientSearchBoxDirective.ClientSearchBoxDirective = function() {
  return {
    scope: {
    },
    restrict: 'E',
    templateUrl: '/static/angular-components/client/client-search-box.html',
    controller: ClientSearchBoxController,
    controllerAs: 'controller'
  };
};


/**
 * Directive's name in Angular.
 *
 * @const
 * @export
 */
grrUi.client.clientSearchBoxDirective.ClientSearchBoxDirective.directive_name =
    'grrClientSearchBox';

});  // goog.scope
