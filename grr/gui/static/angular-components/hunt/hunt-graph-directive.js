'use strict';

goog.provide('grrUi.hunt.huntGraphDirective.HuntGraphController');
goog.provide('grrUi.hunt.huntGraphDirective.HuntGraphDirective');

goog.scope(function() {


/**
 * Controller for HuntGraphDirective.
 *
 * @constructor
 * @param {!angular.Scope} $scope
 * @param {!angular.jQuery} $element Element this directive operates on.
 * @param {!grrUi.core.apiService.ApiService} grrApiService
 * @ngInject
 */
grrUi.hunt.huntGraphDirective.HuntGraphController = function($scope, $element, grrApiService) {
    /** @private {!angular.Scope} */
    this.scope_ = $scope;

    /** @private {!angular.jQuery} */
    this.element_ = $element;

    /** @private {!grrUi.core.apiService.ApiService} */
    this.grrApiService_ = grrApiService;

    /** @type {string} */
    this.scope_.huntUrn;

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

    this.scope_.$watch('huntUrn', this.onHuntUrnChange_.bind(this));
};

var HuntGraphController = grrUi.hunt.huntGraphDirective.HuntGraphController;


/**
 * Handles huntUrn attribute changes.
 *
 * @private
 */
HuntGraphController.prototype.onHuntUrnChange_ = function() {
    this.hunt = null;
    this.huntSummary = null;

    if (angular.isDefined(this.scope_.huntUrn)) {
        var huntUrnComponents = this.scope_.huntUrn.split('/');
        this.huntId = huntUrnComponents[huntUrnComponents.length - 1];
        this.inProgress = true;

        var url = 'hunts/' + this.huntId + '/client-completion-stats';
        var params = {
            'strip_type_info': 1,
            'size': this.maxSampleSize
        };
        this.grrApiService_.get(url, params).then(
            this.onHuntGraphFetched_.bind(this));
    }
};

/**
 * Called when hunt graph data was fetched.
 * @param {!Object} response Response from the server.
 * @private
 */
HuntGraphController.prototype.onHuntGraphFetched_ = function(response) {
    this.clientStartPoints = this.parseDataPoints_(response.data['start_points']);
    this.clientFinishPoints = this.parseDataPoints_(response.data['complete_points']);
    this.informationAvailable =
        (angular.isArray(this.clientStartPoints) && this.clientStartPoints.length > 0) ||
        (angular.isArray(this.clientFinishPoints) && this.clientFinishPoints.length > 0);

    this.drawGraph_();
    this.inProgress = false;
};

/**
 * Parses the points in the server response to data points.
 * @param {!Array} points The points provided in the server response.
 * @return {!Array} A list of data points.
 * @private
 */
HuntGraphController.prototype.parseDataPoints_ = function(points){
    var result = [];
    angular.forEach(points, function(point){
       result.push([
           point['x_value'],
           point['y_value']
       ]);
    });
    return result;
};

/**
 * Redraws the graph.
 * @private
 */
HuntGraphController.prototype.drawGraph_ = function() {
    var graphElement = $(this.element_)
        .find('.client-completion-graph');

    if (graphElement && this.informationAvailable) {
        $.plot(graphElement, [
            {
                label: "Agents issued.",
                data: this.clientStartPoints
            },
            {
                label: "Agents completed.",
                data: this.clientFinishPoints
            }
        ], {
            series: {
                lines: { show: true },
                points: { show: true }
            },
            xaxis: {
                min: 0,
                tickDecimals: 4
            },
            yaxis: {
                tickDecimals: 0
            }
        });
    }
};


/**
 * Directive for displaying errors of a hunt with a given URN.
 *
 * @return {!angular.Directive} Directive definition object.
 * @ngInject
 * @export
 */
grrUi.hunt.huntGraphDirective.HuntGraphDirective = function() {
    return {
        scope: {
            huntUrn: '='
        },
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
grrUi.hunt.huntGraphDirective.HuntGraphDirective.directive_name =
    'grrHuntGraph';


});  // goog.scope
