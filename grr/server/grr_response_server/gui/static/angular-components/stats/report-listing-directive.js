goog.module('grrUi.stats.reportListingDirective');
goog.module.declareLegacyNamespace();

const reportDescsService = goog.requireType('grrUi.stats.reportDescsService');
const {upperCaseToTitleCase} = goog.require('grrUi.core.utils');



/**
 * Parses the stats/reports API call response and converts it to a
 * jsTree-compatible format.
 *
 * @param {Object} reports The server response field response.data.reports,
 *                         type-stripped.
 * @return {!Array} The report listing in a jsTree-compatible structure.
 */
exports.parseStatsReportsApiResponse = function(reports) {
  const ret = [];
  const reportsByType = {};

  angular.forEach(reports, function(report) {
    const desc = report['desc'];

    const reportType = desc['type'];
    let typeReportListing;

    if (angular.isUndefined(reportsByType[reportType])) {
      typeReportListing = [];
      reportsByType[reportType] = typeReportListing;

      ret.push({
        text: upperCaseToTitleCase(reportType),
        children: typeReportListing,
        state: {opened: true, disabled: true}
      });
    } else {
      typeReportListing = reportsByType[reportType];
    }

    const leaf = {id: desc['name'], text: desc['title'], desc: desc};

    typeReportListing.push(leaf);
  });

  return ret;
};
const parseStatsReportsApiResponse = exports.parseStatsReportsApiResponse;


/**
 * Controller for ReportListingDirective.
 * @unrestricted
 */
const ReportListingController = class {
  /**
   * @param {!angular.Scope} $scope
   * @param {!angular.jQuery} $element
   * @param {!reportDescsService.ReportDescsService}
   *     grrReportDescsService
   * @ngInject
   */
  constructor($scope, $element, grrReportDescsService) {
    /** @private {!angular.Scope} */
    this.scope_ = $scope;

    /** @private {!angular.jQuery} */
    this.element_ = $element;

    /** @private {!reportDescsService.ReportDescsService} */
    this.grrReportDescsService_ = grrReportDescsService;

    /** @private {!Object} */
    this.treeElement_ = this.element_.find('.report-listing-tree');

    /** @private {!Object} */
    this.tree_;

    /** @private {string} */
    this.selectionName_;

    /** @private {Object} */
    this.reportListing_;

    this.grrReportDescsService_.getDescs().then(function(reports) {
      this.reportListing_ = parseStatsReportsApiResponse(reports);

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
  }

  /**
   * Initializes the jsTree instance.
   *
   * @private
   */
  initTree_() {
    this.treeElement_.jstree({'core': {'data': this.reportListing_}});
    this.tree_ = this.treeElement_.jstree(true);

    this.treeElement_.on('loaded.jstree', function(event, data) {
      this.updateTreeSelection_();
    }.bind(this));

    this.treeElement_.on('select_node.jstree', function(event, data) {
      const desc = data['node']['original']['desc'];
      this.selectionName_ = desc['name'];
    }.bind(this));
  }

  /**
   * Selects the jsTree element corresponding to this.selectionName_. If the
   * tree is not fully loaded this will do nothing and return silently. Note
   * that this is also what calls to jsTree's methods do.
   *
   * @private
   */
  updateTreeSelection_() {
    if (angular.isUndefined(this.tree_)) {
      return;
    }

    this.tree_['deselect_all']();
    this.tree_['select_node'](this.selectionName_);
  }
};



/**
 * ReportListingDirective definition.
 * @return {angular.Directive} Directive definition object.
 */
exports.ReportListingDirective = function() {
  return {
    restrict: 'E',
    scope: {selectionName: '=?'},
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
exports.ReportListingDirective.directive_name = 'grrReportListing';
