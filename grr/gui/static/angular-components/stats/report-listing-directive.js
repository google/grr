'use strict';

goog.provide('grrUi.stats.reportListingDirective.ReportListingController');
goog.provide('grrUi.stats.reportListingDirective.ReportListingDirective');
goog.provide('grrUi.stats.reportListingDirective.parseStatsReportsApiResponse');

goog.require('grrUi.core.apiService.stripTypeInfo');
goog.require('grrUi.core.utils.upperCaseToTitleCase');

goog.scope(function() {

/**
 * Parses the stats/reports API call response and converts it to a
 * jsTree-compatible format.
 *
 * @param {Object} typedReports The server response field response.data.reports
 * @return {Array} The report listing in a jsTree-compatible structure.
 */
grrUi.stats.reportListingDirective.parseStatsReportsApiResponse =
    function(typedReports) {
  var ret = [];
  var reportsByType = {};

  var reports = /** @type {Object} */ (
      grrUi.core.apiService.stripTypeInfo(typedReports));

  angular.forEach(reports, function(report) {
    var desc = report['desc'];

    var reportType = desc['type'];
    var typeReportListing;

    if (angular.isUndefined(reportsByType[reportType])) {
      typeReportListing = [];
      reportsByType[reportType] = typeReportListing;

      ret.push({
        text: grrUi.core.utils.upperCaseToTitleCase(reportType),
        children: typeReportListing,
        state: {
          opened: true,
          disabled: true
        }
      });
    }
    else {
      typeReportListing = reportsByType[reportType];
    }

    var leaf = {
      id: desc['name'],
      text: desc['title'],
      desc: desc
    };

    typeReportListing.push(leaf);
  });

  return ret;
};


/**
 * Controller for ReportListingDirective.
 *
 * @constructor
 * @param {!angular.Scope} $rootScope
 * @param {!angular.Scope} $scope
 * @param {!angular.jQuery} $element
 * @param {!grrUi.core.apiService.ApiService} grrApiService
 * @ngInject
 */
grrUi.stats.reportListingDirective.ReportListingController = function(
    $rootScope, $scope, $element, grrApiService) {
  /** @private {!angular.Scope} */
  this.rootScope_ = $rootScope;

  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @private {!angular.jQuery} */
  this.element_ = $element;

  /** @private {!Object} */
  this.treeElement_ = this.element_.find('.report-listing-tree');

  /** @private {!Object} */
  this.tree_;

  /** @private {!grrUi.core.apiService.ApiService} */
  this.grrApiService_ = grrApiService;

  /** @private {string} */
  this.selectionName_;

  /** @private {Object} */
  this.reportListing_;

  this.grrApiService_.get('stats/reports').then(function(response) {
    this.reportListing_ =
        grrUi.stats.reportListingDirective.parseStatsReportsApiResponse(
            response['data']['reports']);

    this.initTree_();
  }.bind(this));

  this.scope_.$watch('selectionName', function(selectionName) {
    if (angular.isUndefined(selectionName)) {
      return;
    }

    this.selectionName_ = selectionName;
  }.bind(this));

  this.scope_.$watch('controller.selectionName_', function() {
    if (angular.isUndefined(this.selectionName_)) {
      return;
    }

    this.scope_['selectionName'] = this.selectionName_;
    this.updateTreeSelection_();
  }.bind(this));
};
var ReportListingController =
    grrUi.stats.reportListingDirective.ReportListingController;


/**
 * Initializes the jsTree instance.
 *
 * @private
 */
ReportListingController.prototype.initTree_ = function() {
  this.treeElement_.jstree({
    'core' : {
      'data' : this.reportListing_
    }
  });
  this.tree_ = this.treeElement_.jstree(true);

  this.treeElement_.on('loaded.jstree', function(event, data) {
    this.updateTreeSelection_();
  }.bind(this));

  this.treeElement_.on('select_node.jstree', function(event, data) {
    var desc = data['node']['original']['desc'];
    this.selectionName_ = desc['name'];
  }.bind(this));
};

/**
 * Selects the jsTree element corresponding to this.selectionName_. If the tree
 * is not fully loaded this will do nothing and return silently. Note that this
 * is also what calls to jsTree's methods do.
 *
 * @private
 */
ReportListingController.prototype.updateTreeSelection_ = function() {
  if (angular.isUndefined(this.tree_)) {
    return;
  }

  this.tree_['deselect_all']();
  this.tree_['select_node'](this.selectionName_);
};

/**
 * ReportListingDirective definition.
 * @return {angular.Directive} Directive definition object.
 */
grrUi.stats.reportListingDirective.ReportListingDirective = function() {
  return {
    restrict: 'E',
    scope: {
      selectionName: '=?'
    },
    templateUrl: '/static/angular-components/stats/report-listing.html',
    controller: ReportListingController,
    controllerAs: 'controller',
  };
};


/**
 * Name of the directive in Angular.
 *
 * @const
 * @export
 */
grrUi.stats.reportListingDirective.ReportListingDirective.directive_name =
    'grrReportListing';

});  // goog.scope
