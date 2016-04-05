'use strict';

goog.provide('grrUi.flow.flowsListDirective.FlowsListController');
goog.provide('grrUi.flow.flowsListDirective.FlowsListDirective');
goog.provide('grrUi.flow.flowsListDirective.flattenFlowsList');
goog.provide('grrUi.flow.flowsListDirective.toggleFlowExpansion');

goog.scope(function() {


/**
 * Flattens list of flows returned by the server. Every flow in the list
 * can have 'nested_flows' attribute with a list of child flows. This
 * function flattens this tree-like structure into a simple list and
 * assigns depth to every element in the list.
 *
 * @param {!Array<Object>} flows List of flows to flatten.
 * @param {number=} opt_currentDepth Current depth, defaults to 0.
 * @return {!Array<Object>} Flattened list of flows.
 *
 * @export
 */
grrUi.flow.flowsListDirective.flattenFlowsList = function(
    flows, opt_currentDepth) {
  if (angular.isUndefined(opt_currentDepth)) {
    opt_currentDepth = 0;
  }

  var result = [];
  for (var i = 0; i < flows.length; ++i) {
    var flow = angular.copy(flows[i]);
    flow['depth'] = opt_currentDepth;

    result.push(flow);
    if (angular.isDefined(flow['value']) &&
        angular.isDefined(flow['value']['nested_flows'])) {
      result = result.concat(
          grrUi.flow.flowsListDirective.flattenFlowsList(
              flow['value']['nested_flows'], opt_currentDepth + 1));

      delete flow['value']['nested_flows'];
    }
  }
  return result;
};
var flattenFlowsList = grrUi.flow.flowsListDirective.flattenFlowsList;


/**
 * Toggles 'shown' attribute on flows[index]. When making the flow visible,
 * all direct children become visible. Indirect children become visible only
 * if their respective parents were previously expanded. When hiding the flow,
 * all direct and indirect children become hidden.
 *
 * @param {Array<Object>} flows Flattened list of flows.
 * @param {number} index Index of a flow to be expanded.
 * @return {Array<Object>} Returns list of flows passed in "flows" argument.
 *     Note that it's modified inplace, no copies are created.
 *
 * @export
 */
grrUi.flow.flowsListDirective.toggleFlowExpansion = function(flows, index) {
  var flowToExpand = flows[index];
  var i;

  flowToExpand.expanded = !flowToExpand.expanded;

  if (!flowToExpand.expanded) {
    for (i = index + 1; i < flows.length; ++i) {
      if (flows[i].depth > flowToExpand.depth) {
        flows[i].shown = false;
      } else {
        break;
      }
    }
  } else {
    // If this is not null, ignore all flows with a depth > ignoreDepth.
    var ignoreDepth = null;
    for (i = index + 1; i < flows.length; ++i) {

      if (flows[i].depth > flowToExpand.depth) {

        if (!ignoreDepth || ignoreDepth >= flows[i].depth) {
          flows[i].shown = true;

          // If this flow was expanded, we want to show its immediate children,
          // so we set ignoreDepth to null. Otherwise we set ignoreDepth
          // to flows's depth. This way all direct and indirect children of
          // flows[i] will get ignored and their "shown" attribute won't get
          // flipped.
          //
          // It's important to note that when ignoreDepth is set to
          // flow's depth, flow's sibling flows are not affected, as they have
          // depth which is equal to ignoreDepth (see the condition above).
          //
          // Example:
          // A (depth = 0, expanded = false)
          //   B (depth = 1, expanded = false)
          //     C (depth = 2, expanded = false)
          //   D (depth = 1, expanded = false)
          //
          // Let's say toggleFlowExpansion is called on A:
          // 1. B.shown is set to true. ignoreDepth is set to 1, because
          //    B.expanded is False.
          // 2. C is skipped, because its depth (2) is greater than
          //    ignoreDepth (1).
          // 3. D.shown is set to true, because its depth (1) is equal
          //    to ignoredepth (1). ignoreDepth is set to 1.
          ignoreDepth = flows[i].expanded ? null : flows[i].depth;
        }

      } else {
        break;
      }
    }
  }

  return flows;
};
var toggleFlowExpansion = grrUi.flow.flowsListDirective.toggleFlowExpansion;


/**
 * Controller for FlowsListDirective.
 *
 * @constructor
 * @param {!angular.Scope} $scope
 * @param {!angular.jQuery} $element
 * @param {!grrUi.core.apiService.ApiService} grrApiService
 * @ngInject
 */
grrUi.flow.flowsListDirective.FlowsListController = function(
    $scope, $element, grrApiService) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @private {!angular.jQuery} */
  this.element_ = $element;

  /** @type {!Object<string, Object>} */
  this.flowsByUrn = {};

  /** @type {?string} */
  this.selectedFlowUrn;

  // Push the selection changes back to the scope, so that other UI components
  // can react on the change.
  this.scope_.$watch('controller.selectedFlowUrn', function(newValue) {
    // Only propagate real changes, don't propagate initial undefined
    // value.
    if (angular.isDefined(newValue)) {
      this.scope_['selectedFlowUrn'] = newValue;
    }
  }.bind(this));

  // If outer binding changes, we want to update our selection.
  this.scope_.$watch('selectedFlowUrn', function(newValue) {
    if (angular.isDefined(newValue)) {
      this.selectedFlowUrn = newValue;
    }
  }.bind(this));
};
var FlowsListController = grrUi.flow.flowsListDirective.FlowsListController;


/**
 * Selects given item in the list.
 *
 * @param {!Object} item Item to be selected.
 * @export
 */
FlowsListController.prototype.selectItem = function(item) {
  this.selectedFlowUrn = item['value']['urn']['value'];
};


/**
 * Transforms items fetched by API items provider so that they can be
 * correctly presented as flows tree.
 *
 * @param {!Array<Object>} items Items to be transformed.
 * @return {!Array<Object>} Transformed items.
 * @export
 */
FlowsListController.prototype.transformItems = function(items) {
  var flattenedItems = flattenFlowsList(items);

  angular.forEach(flattenedItems, function(item, index) {
    var urn = item['value']['urn']['value'];
    this.flowsByUrn[urn] = item;

    var components = urn.split('/');
    item.shortUrn = components[components.length - 1];
    item.shown = item.depth == 0;
    if (index < flattenedItems.length - 1 &&
        flattenedItems[index + 1].depth > item.depth) {
      item.expanded = false;
    }

    item.expand = function(e) {
      e.stopPropagation();
      toggleFlowExpansion(flattenedItems, index);
    };
  }.bind(this));

  return flattenedItems;
};


/**
 * FlowsListDirective definition.

 * @return {angular.Directive} Directive definition object.
 */
grrUi.flow.flowsListDirective.FlowsListDirective = function() {
  return {
    scope: {
      flowsUrl: '=',
      selectedFlowUrn: '=?',
      triggerUpdate: '=?'
    },
    restrict: 'E',
    templateUrl: '/static/angular-components/flow/flows-list.html',
    controller: FlowsListController,
    controllerAs: 'controller'
  };
};


/**
 * Directive's name in Angular.
 *
 * @const
 * @export
 */
grrUi.flow.flowsListDirective.FlowsListDirective
    .directive_name = 'grrFlowsList';



});  // goog.scope
