'use strict';

goog.provide('grrUi.forms.dictFormDirective.DictFormController');
goog.provide('grrUi.forms.dictFormDirective.DictFormDirective');


goog.scope(function() {

/**
 * Controller for DictFormDirective.
 *
 * @constructor
 * @param {!angular.Scope} $scope
 * @param {!grrUi.core.reflectionService.ReflectionService} grrReflectionService
 * @ngInject
 */
grrUi.forms.dictFormDirective.DictFormController = function(
    $scope, grrReflectionService) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @private {!grrUi.core.reflectionService.ReflectionService} */
  this.grrReflectionService_ = grrReflectionService;

  /** @type {Array<Object>} */
  this.keyValueList;

  /** @type {Object} */
  this.keyValueDescriptor;

  /** @type {Object} */
  this.stringDefault;

  this.grrReflectionService_.getRDFValueDescriptor('RDFString').then(
      function(descriptor) {
        this.stringDefault = descriptor['default'];

        // Only initialize watchers after the description is fetched.
        this.scope_.$watch('controller.keyValueList',
                           this.onKeyValueListChange_.bind(this),
                           true);
        this.scope_.$watch('value.value', this.onValueChange_.bind(this), true);
      }.bind(this));

};
var DictFormController = grrUi.forms.dictFormDirective.DictFormController;


/**
 * Handles changes in key-value list (key-value list is a presentation-friendly
 * format). Gets converted into dictionary which is assigned to the 'value'
 * binding.
 *
 * @param {Array<Object>} newValue New list of key-value pairs.
 * @private
 */
DictFormController.prototype.onKeyValueListChange_ = function(newValue) {
  if (angular.isDefined(newValue)) {
    this.scope_.value.value = {};
    for (var i = 0; i < this.keyValueList.length; ++i) {
      var pair = this.keyValueList[i];
      this.scope_.value.value[pair['key']] = pair['value'];
    }
  }
};


/**
 * Handles changes in the bound value. Updates presentation-friendly
 * key-value list. Note that both onKeyValueListChange_ and onValueChange_
 * are designed in such a way so they don't cause infinite watch loop
 * when either of them changes.
 *
 * @param {Object} newValue New dictionary value.
 * @private
 */
DictFormController.prototype.onValueChange_ = function(newValue) {
  if (angular.isObject(newValue)) {
    if (angular.isUndefined(this.keyValueList)) {
      this.keyValueList = [];
    }

    angular.forEach(newValue, function(value, key) {
      var found = false;
      for (var i = 0; i < this.keyValueList.length; ++i) {
        var pair = this.keyValueList[i];
        if (pair['key'] == key) {
          found = true;
          pair['value'] = value;
        }
      }

      if (!found) {
        this.keyValueList.push({key: key, value: value});
      }
    }.bind(this));
  } else {
    this.keyValueList = [];
  }
};

/**
 * Adds pair to the list of key-value pairs.
 *
 * @export
 */
DictFormController.prototype.addPair = function() {
  this.keyValueList.push({key: '',
                          value: angular.copy(this.stringDefault)});
};


/**
 * Removes pair with a given index from a list of key-value pairs.
 *
 * @param {number} index Index of the pair to be removed.
 * @export
 */
DictFormController.prototype.removePair = function(index) {
  this.keyValueList.splice(index, 1);
};


/**
 * DictFormDirective definition.
 *
 * @return {angular.Directive} Directive definition object.
 */
grrUi.forms.dictFormDirective.DictFormDirective = function() {
  return {
    restrict: 'E',
    scope: {
      value: '='
    },
    templateUrl: '/static/angular-components/forms/dict-form.html',
    controller: DictFormController,
    controllerAs: 'controller'
  };
};


/**
 * Directive's name in Angular.
 *
 * @const
 * @export
 */
grrUi.forms.dictFormDirective.DictFormDirective
    .directive_name = 'grrFormDict';


/**
 * Semantic types corresponding to this directive.
 *
 * @const
 * @export
 */
grrUi.forms.dictFormDirective.DictFormDirective
    .semantic_types = ['dict', 'Dict'];


});  // goog.scope
