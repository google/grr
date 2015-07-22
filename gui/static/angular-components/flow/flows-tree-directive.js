'use strict';

goog.provide('grrUi.flow.flowsTreeDirective.FlowsTreeController');
goog.provide('grrUi.flow.flowsTreeDirective.FlowsTreeDirective');

goog.scope(function() {



/**
 * Controller for FlowsTreeDirective.
 *
 * @constructor
 * @param {!angular.Scope} $scope
 * @param {!angular.JQLite} $element
 * @param {!grrUi.core.apiService.ApiService} grrApiService
 * @ngInject
 */
grrUi.flow.flowsTreeDirective.FlowsTreeController = function(
    $scope, $element, grrApiService) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @private {!angular.JQLite} */
  this.element_ = $element;

  /** @private {!grrUi.core.apiService.ApiService} */
  this.grrApiService_ = grrApiService;

  this.grrApiService_.get('/flows/descriptors').then(function(response) {
    var flowsDescriptors = response.data;

    var treeNodes = [];
    angular.forEach(Object.keys(flowsDescriptors).sort(), function(category) {
      var categoryNode = {
        data: category,
        // Id is needed for Selenium tests backwards compatibility.
        attr: {id: '_' + category},
        state: 'closed',
        children: []
      };

      var descriptors = flowsDescriptors[category].sort(function(a, b) {
        var aName = a['friendly_name'] || a['name'];
        var bName = b['friendly_name'] || b['name'];

        if (aName < bName) {
          return -1;
        } else if (aName > bName) {
          return 1;
        } else {
          return 0;
        }
      });
      angular.forEach(descriptors, function(descriptor) {
        categoryNode['children'].push({
          metadata: {descriptor: descriptor},
          // Id is needed for Selenium tests backwards compatibility.
          attr: {id: '_' + category + '-' + descriptor['name']},
          data: descriptor['friendly_name'] || descriptor['name']
        });
      }.bind(this));

      treeNodes.push(categoryNode);
    }.bind(this));

    var treeElem = $(this.element_).children('div.tree');
    treeElem.jstree({
      'json_data': {
        'data': treeNodes,
      },
      'plugins': ['json_data', 'themes', 'ui']
    });
    treeElem.on('select_node.jstree', function(e, data) {
      data['inst']['toggle_node'](data['rslt']['obj']);

      var descriptor = data['rslt']['obj'].data('descriptor');
      if (angular.isDefined(descriptor)) {
        // Have to call apply as we're in event handler triggered by
        // non-Angular code.
        this.scope_.$apply(function() {
          this.scope_.selectedDescriptor = descriptor;
        }.bind(this));
      }
    }.bind(this));
  }.bind(this));
};
var FlowsTreeController = grrUi.flow.flowsTreeDirective.FlowsTreeController;


/**
 * FlowsTreeDirective definition.

 * @return {angular.Directive} Directive definition object.
 */
grrUi.flow.flowsTreeDirective.FlowsTreeDirective = function() {
  return {
    scope: {
      selectedDescriptor: '=?'
    },
    restrict: 'E',
    template: '<div class="tree"></div>',
    controller: FlowsTreeController,
    controllerAs: 'controller'
  };
};


/**
 * Directive's name in Angular.
 *
 * @const
 * @export
 */
grrUi.flow.flowsTreeDirective.FlowsTreeDirective.directive_name =
    'grrFlowsTree';



});  // goog.scope
