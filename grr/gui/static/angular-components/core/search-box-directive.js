'use strict';

goog.provide('grrUi.core.searchBoxDirective.SearchBoxController');
goog.provide('grrUi.core.searchBoxDirective.SearchBoxDirective');


goog.scope(function() {

var SEARCH_KEYWORDS = ['host', 'mac', 'ip', 'user', 'label'];

/**
 * Controller for SearchBoxDirective.
 *
 * @constructor
 * @param {!angular.Scope} $scope
 * @param {!angular.jQuery} $element
 * @param {!angular.$interval} $interval
 * @param {!grrUi.core.apiService.ApiService} grrApiService
 * @ngInject
 */
grrUi.core.searchBoxDirective.SearchBoxController = function(
    $scope, $element, $interval, grrApiService) {

  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @private {!angular.jQuery} */
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

var SearchBoxController =
    grrUi.core.searchBoxDirective.SearchBoxController;


/**
 * Handles /clients/labels response.
 *
 * @param {!Object} response
 * @private
 */
SearchBoxController.prototype.onGetLabels_ = function(response) {
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
SearchBoxController.prototype.submitQuery = function() {
  if (this.isShaHash_(this.query)) {
    grr.layout('FilestoreTable', 'main', {q: this.query});
  } else if (this.isHuntId_(this.query)) {
    this.checkHunt_(this.query);
  } else {
    grr.publish('hash_state', 'main', 'HostTable');
    grr.publish('hash_state', 'q', this.query);
    grr.layout('HostTable', 'main', {q: this.query});
  }
};

/**
 * Checks if the passed string is a SHA hash.
 * @param {string} input A string potentially describing a SHA hash.
 * @return {boolean} True if the string is a SHA hash, false otherwise.
 * @private
 */
SearchBoxController.prototype.isShaHash_ = function(input) {
  var sha_regex = /^[A-F0-9]{64}$/i;
  return sha_regex.test(input);
};

/**
 * Checks if the passed string may be a hunt id.
 * @param {string} input A string potentially describing a hunt id.
 * @return {boolean} True if the string might be a hunt id, false otherwise.
 * @private
 */
SearchBoxController.prototype.isHuntId_ = function(input) {
  var hunt_regex = /^[A-Z0-9]+:[A-F0-9]{6,12}$/i;

  if (!hunt_regex.test(input)) {
    return false;
  }

  // If the first part of the potential hunt id equals a reserved search
  // keyword, we do not consider it a hunt id.
  var components = input.split(':');
  var potential_keyword = components[0].toLowerCase();
  return SEARCH_KEYWORDS.indexOf(potential_keyword) === -1;
};

/**
 * Tries to retrieve the hunt details of a given hunt id. If successfull, forwards
 * the user to the hunt details. If not successfull, performs a regular client search.
 * @param {string} huntId The id of the hunt to check for existance.
 * @private
 */
SearchBoxController.prototype.checkHunt_ = function(huntId) {
  this.grrApiService_.get('hunts/' + huntId).then(
    function success(response) {
      var huntUrn = response.data['urn'];
      grr.publish('hash_state', 'hunt_id', huntUrn);
      grr.publish('hash_state', 'main', 'ManageHunts');
      grr.publish('hunt_selection', huntUrn);
    }.bind(this),
    function error() {
      // Hunt not found, revert to regular client search.
      grr.publish('hash_state', 'main', 'HostTable');
      grr.publish('hash_state', 'q', this.query);
      grr.layout('HostTable', 'main', {q: this.query});
    }.bind(this)
  );
};


/**
 * @export {string}
 * @const
 */
SearchBoxController.prototype.contextHelpUrl =
    'user_manual.html#searching-for-a-client';


/**
 * Displays a table of clients.
 *
 * @return {angular.Directive} Directive definition object.
 */
grrUi.core.searchBoxDirective.SearchBoxDirective = function() {
  return {
    scope: {
    },
    restrict: 'E',
    templateUrl: '/static/angular-components/core/search-box.html',
    controller: SearchBoxController,
    controllerAs: 'controller'
  };
};


/**
 * Directive's name in Angular.
 *
 * @const
 * @export
 */
grrUi.core.searchBoxDirective.SearchBoxDirective.directive_name =
    'grrSearchBox';

});  // goog.scope
