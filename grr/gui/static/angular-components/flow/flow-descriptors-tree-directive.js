'use strict';

goog.provide('grrUi.flow.flowDescriptorsTreeDirective.FlowDescriptorsTreeController');
goog.provide('grrUi.flow.flowDescriptorsTreeDirective.FlowDescriptorsTreeDirective');

goog.scope(function() {



/**
 * Controller for FlowDescriptorsTreeDirective.
 *
 * @constructor
 * @param {!angular.Scope} $scope
 * @param {!angular.jQuery} $element
 * @param {!grrUi.core.apiService.ApiService} grrApiService
 * @ngInject
 */
grrUi.flow.flowDescriptorsTreeDirective.FlowDescriptorsTreeController =
    function($scope, $element, grrApiService) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @private {!angular.jQuery} */
  this.element_ = $element;

  /** @private {!grrUi.core.apiService.ApiService} */
  this.grrApiService_ = grrApiService;

  /** @type {!Object} */
  this.flowsDescriptors;

  /** @type {!Object} */
  this.userSettings;

  this.grrApiService_.get('/users/me/settings').then(function(response) {
    this.userSettings = response.data;
  }.bind(this));

  this.scope_.$watch('flowType', this.onFlowTypeChange_.bind(this));
  this.scope_.$watchGroup(['controller.userSettings',
                           'controller.flowsDescriptors'],
                          this.onDescriptorsOrSettingsChange_.bind(this));
};
var FlowDescriptorsTreeController =
    grrUi.flow.flowDescriptorsTreeDirective.FlowDescriptorsTreeController;


/**
 * Handles changes in flowType binding,
 *
 * @param {?string} newValue New flowType binding value.
 * @private
 */
FlowDescriptorsTreeController.prototype.onFlowTypeChange_ = function(newValue) {
  var params = {};

  if (angular.isDefined(newValue)) {
    if (newValue == 'CLIENT') {
      params['flow_type'] = 'client';
    } else if (newValue == 'GLOBAL') {
      params['flow_type'] = 'global';
    } else {
      throw new Error('Unknown flow type: ' + newValue);
    }
  }

  this.grrApiService_.get('/flows/descriptors', params).then(
      function(response) {
        this.flowsDescriptors = response.data;
      }.bind(this));
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
      // Filter out flows that don't support display mode selected by
      // the user.
      if (mode == 'DEBUG' || descriptor['behaviours'].indexOf(mode) != -1) {

        categoryNode['children'].push({
          data: {descriptor: descriptor},
          // Id is needed for Selenium tests backwards compatibility.
          li_attr: {id: '_' + category + '-' + descriptor['name']},
          text: descriptor['friendly_name'] || descriptor['name'],
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
grrUi.flow.flowDescriptorsTreeDirective.FlowDescriptorsTreeDirective =
    function() {
  return {
    scope: {
      flowType: '=?',
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
grrUi.flow.flowDescriptorsTreeDirective.FlowDescriptorsTreeDirective
    .directive_name = 'grrFlowDescriptorsTree';



});  // goog.scope
