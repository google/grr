goog.module('grrUi.core.searchBoxDirective');
goog.module.declareLegacyNamespace();

const apiService = goog.requireType('grrUi.core.apiService');
const routingService = goog.requireType('grrUi.routing.routingService');



/** @const */
var SEARCH_KEYWORDS = ['host', 'mac', 'ip', 'user', 'label'];

/**
 * Controller for SearchBoxDirective.
 * @unrestricted
 */
const SearchBoxController = class {
  /**
   * @param {!angular.Scope} $scope
   * @param {!angular.jQuery} $element
   * @param {!angular.$interval} $interval
   * @param {!apiService.ApiService} grrApiService
   * @param {!routingService.RoutingService} grrRoutingService
   * @ngInject
   */
  constructor($scope, $element, $interval, grrApiService, grrRoutingService) {
    /** @private {!angular.Scope} */
    this.scope_ = $scope;

    /** @private {!angular.jQuery} */
    this.element_ = $element;

    /** @private {!angular.$interval} */
    this.interval_ = $interval;

    /** @private {!apiService.ApiService} */
    this.grrApiService_ = grrApiService;

    /** @private {!routingService.RoutingService} */
    this.grrRoutingService_ = grrRoutingService;

    /** @export {string} */
    this.query = '';

    /** @export {Array} */
    this.labels = [];

    this.grrApiService_.get('/clients/labels')
        .then(this.onGetLabels_.bind(this));
  }

  /**
   * Handles /clients/labels response.
   *
   * @param {!Object} response
   * @private
   */
  onGetLabels_(response) {
    angular.forEach(response['data']['items'], function(label) {
      this.labels.push('label:' + label['value']['name']['value']);
    }.bind(this));
  }

  /**
   * Updates GRR UI with current query value (using legacy API).
   *
   * @export
   */
  submitQuery() {
    if (this.isHuntId_(this.query)) {
      this.checkHunt_(this.query);
    } else {
      this.grrRoutingService_.go('search', {q: this.query});
    }
  }

  /**
   * Checks if the passed string may be a hunt id.
   * @param {string} input A string potentially describing a hunt id.
   * @return {boolean} True if the string might be a hunt id, false otherwise.
   * @private
   */
  isHuntId_(input) {
    var huntRegex = /^([A-Z0-9]+:)?[A-F0-9]{6,16}$/i;

    if (!huntRegex.test(input)) {
      return false;
    }

    // If the first part of the potential hunt id equals a reserved search
    // keyword, we do not consider it a hunt id.
    var components = input.split(':');
    var potential_keyword = components[0].toLowerCase();
    return SEARCH_KEYWORDS.indexOf(potential_keyword) === -1;
  }

  /**
   * Tries to retrieve the hunt details of a given hunt id. If successful,
   * forwards the user to the hunt details. If not successful, performs a
   * regular client search.
   *
   * @param {string} huntId The id of the hunt to check for existence.
   * @private
   */
  checkHunt_(huntId) {
    this.grrApiService_.get('hunts/' + huntId)
        .then(
            function success(response) {
              var huntId = response.data['value']['hunt_id']['value'];
              this.grrRoutingService_.go('hunts', {huntId: huntId});
            }.bind(this),
            function error() {
              // Hunt not found, revert to regular client search.
              this.grrRoutingService_.go('search', {q: this.query});
            }.bind(this));
  }
};



/**
 * @export {string}
 * @const
 */
SearchBoxController.prototype.contextHelpUrl =
    'investigating-with-grr/searching-for-client.html';


/**
 * Displays a table of clients.
 *
 * @return {angular.Directive} Directive definition object.
 */
exports.SearchBoxDirective = function() {
  return {
    scope: {},
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
exports.SearchBoxDirective.directive_name = 'grrSearchBox';
