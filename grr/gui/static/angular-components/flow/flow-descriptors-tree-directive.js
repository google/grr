'use strict';

goog.module('grrUi.flow.flowDescriptorsTreeDirective');
goog.module.declareLegacyNamespace();

const {ApiService, stripTypeInfo} = goog.require('grrUi.core.apiService');



/**
 * Controller for FlowDescriptorsTreeDirective.
 *
 * @constructor
 * @param {!angular.Scope} $scope
 * @param {!angular.jQuery} $element
 * @param {!ApiService} grrApiService
 * @ngInject
 */
const FlowDescriptorsTreeController =
    function($scope, $element, grrApiService) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @private {!angular.jQuery} */
  this.element_ = $element;

  /** @private {!ApiService} */
  this.grrApiService_ = grrApiService;

  /** @type {!Object<string, Array<Object>>} */
  this.flowsDescriptors;

  /** @type {!Object} */
  this.userSettings;

  this.grrApiService_.get('/users/me').then(function(response) {
    this.userSettings = response.data['value']['settings'];
  }.bind(this));

  this.grrApiService_.get('/flows/descriptors').then(
      function(response) {
        this.flowsDescriptors = this.groupDescriptorsByCategory_(
            response['data']['items']);
      }.bind(this));

  this.scope_.$watchGroup(['controller.userSettings',
                           'controller.flowsDescriptors'],
                          this.onDescriptorsOrSettingsChange_.bind(this));

};


/**
 * Converts flow descriptors list to a dictionary where descriptors are grouped
 * by category.
 *
 * @param {Array<Object>} items List of descriptors to convert.
 * @return {!Object<string, Array<Object>>} Dictionary with descriptors grouped
 *     by category.
 * @private
 */
FlowDescriptorsTreeController.prototype.groupDescriptorsByCategory_ =
    function(items) {
  var result = {};
  angular.forEach(items, function(item) {
    var category = item['value']['category']['value'];
    result[category] = result[category] || [];
    result[category].push(item);
  }.bind(this));

  return result;
};


/**
 * Handles data necessary to build the tree: list of flows descriptors and
 * user settings (settings contain UI mode - BASIC/ADVANCED/DEBUG) necessary
 * to filter the flow tree.
 *
 * @private
 */
FlowDescriptorsTreeController.prototype.onDescriptorsOrSettingsChange_ =
    function() {
  if (angular.isUndefined(this.flowsDescriptors) ||
      angular.isUndefined(this.userSettings)) {
    return;
  }

  // Get current UI mode selected by the user. Default to "BASIC" if
  // it's not set.
  // TODO(user): stuff like this should be abstracted away into a
  // dedicated service.
  var mode = this.scope_.$eval('controller.userSettings.value.mode.value');
  if (angular.isUndefined(mode)) {
    mode = 'BASIC';
  }

  var treeNodes = [];
  var descriptorsKeys = Object.keys(this.flowsDescriptors).sort();
  angular.forEach(descriptorsKeys, function(category) {
    var categoryNode = {
      text: category,
      // Id is needed for Selenium tests backwards compatibility.
      li_attr: {id: '_' + category},
      children: []
    };

    var descriptors = this.flowsDescriptors[category].sort(function(a, b) {
      a = stripTypeInfo(a);
      b = stripTypeInfo(b);

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
      var strippedDescriptor = stripTypeInfo(descriptor);

      // Filter out flows that don't support display mode selected by
      // the user.
      if (mode == 'DEBUG' ||
          strippedDescriptor['behaviours'].indexOf(mode) != -1) {

        categoryNode['children'].push({
          data: {descriptor: descriptor},
          // Id is needed for Selenium tests backwards compatibility.
          li_attr: {id: '_' + category + '-' + strippedDescriptor['name']},
          text: (strippedDescriptor['friendly_name'] ||
              strippedDescriptor['name']),
          icon: 'file'
        });
      }
    }.bind(this));

    treeNodes.push(categoryNode);
  }.bind(this));

  var treeElem = $(this.element_).children('div.tree');
  treeElem.jstree({
    'core': {
      'data': treeNodes,
    }
  });
  treeElem.on('select_node.jstree', function(e, data) {
    data['instance']['toggle_node'](data['node']);

    if (data.node.data !== null) {
      var descriptor = data.node.data.descriptor;

      // Have to call apply as we're in event handler triggered by
      // non-Angular code.
      this.scope_.$apply(function() {
        this.scope_.selectedDescriptor = descriptor;
      }.bind(this));
    }
  }.bind(this));
};


/**
 * FlowDescriptorsTreeDirective definition.

 * @return {angular.Directive} Directive definition object.
 */
exports.FlowDescriptorsTreeDirective = function() {
  return {
    scope: {
      selectedDescriptor: '=?'
    },
    restrict: 'E',
    template: '<div class="tree"></div>',
    controller: FlowDescriptorsTreeController,
    controllerAs: 'controller'
  };
};


/**
 * Directive's name in Angular.
 *
 * @const
 * @export
 */
exports.FlowDescriptorsTreeDirective.directive_name = 'grrFlowDescriptorsTree';
