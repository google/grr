goog.module('grrUi.hunt.huntGraphDirective');
goog.module.declareLegacyNamespace();

const apiService = goog.requireType('grrUi.core.apiService');
const {buildTimeseriesGraph} = goog.require('grrUi.stats.graphUtils');


/**
 * Controller for HuntGraphDirective.
 * @unrestricted
 */
const HuntGraphController = class {
  /**
   * @param {!angular.Scope} $scope
   * @param {!angular.jQuery} $element Element this directive operates on.
   * @param {!apiService.ApiService} grrApiService
   * @ngInject
   */
  constructor($scope, $element, grrApiService) {
    /** @private {!angular.Scope} */
    this.scope_ = $scope;

    /** @private {!angular.jQuery} */
    this.element_ = $element;

    /** @private {!apiService.ApiService} */
    this.grrApiService_ = grrApiService;

    /** @type {string} */
    this.scope_.huntId;

    /** @export {boolean} */
    this.inProgress = false;

    /** @export {Array} */
    this.clientStartPoints;

    /** @export {Array} */
    this.clientFinishPoints;

    /** @export {boolean} */
    this.informationAvailable;

    /** @export {number} */
    this.maxSampleSize = 1000;

    this.scope_.$watch('huntId', this.onHuntIdChange_.bind(this));
  }

  /**
   * Handles huntId attribute changes.
   *
   * @private
   */
  onHuntIdChange_() {
    this.hunt = null;
    this.huntSummary = null;

    if (angular.isDefined(this.scope_.huntId)) {
      this.huntId = this.scope_['huntId'];
      this.inProgress = true;

      var url = 'hunts/' + this.huntId + '/client-completion-stats';
      var params = {'strip_type_info': 1, 'size': this.maxSampleSize};
      this.grrApiService_.get(url, params)
          .then(this.onHuntGraphFetched_.bind(this));
    }
  }

  /**
   * Called when hunt graph data was fetched.
   * @param {!Object} response Response from the server.
   * @private
   */
  onHuntGraphFetched_(response) {
    this.clientStartPoints =
        this.parseDataPoints_(response.data['start_points']);
    this.clientFinishPoints =
        this.parseDataPoints_(response.data['complete_points']);
    this.informationAvailable = (angular.isArray(this.clientStartPoints) &&
                                 this.clientStartPoints.length > 0) ||
        (angular.isArray(this.clientFinishPoints) &&
         this.clientFinishPoints.length > 0);

    this.drawGraph_();
    this.inProgress = false;
  }

  /**
   * Parses the points in the server response to data points.
   * @param {!Array} points The points provided in the server response.
   * @return {!Array} A list of data points.
   * @private
   */
  parseDataPoints_(points) {
    var result = [];
    angular.forEach(points, function(point) {
      result.push([
        // Convert floating-point seconds to milliseconds.
        Math.round(point['x_value'] * 1000), point['y_value']
      ]);
    });
    return result;
  }

  /**
   * Redraws the graph.
   * @private
   */
  drawGraph_() {
    var graphElement = $(this.element_).find('.client-completion-graph');

    if (graphElement && this.informationAvailable) {
      graphElement.resize(() => {
        graphElement.html('');

        buildTimeseriesGraph(graphElement, undefined, {
          'Agents issued.': this.clientStartPoints,
          'Agents completed.': this.clientFinishPoints,
        });
      });
      graphElement.resize();
    }
  }
};



/**
 * Directive for displaying errors of a hunt with a given URN.
 *
 * @return {!angular.Directive} Directive definition object.
 * @ngInject
 * @export
 */
exports.HuntGraphDirective = function() {
  return {
    scope: {huntId: '='},
    restrict: 'E',
    templateUrl: '/static/angular-components/hunt/hunt-graph.html',
    controller: HuntGraphController,
    controllerAs: 'controller'
  };
};


/**
 * Directive's name in Angular.
 *
 * @const
 * @export
 */
exports.HuntGraphDirective.directive_name = 'grrHuntGraph';
