'use strict';

goog.module('grrUi.forms.dictFormDirective');
goog.module.declareLegacyNamespace();



/**
 * Controller for DictFormDirective.
 *
 * @constructor
 * @param {!angular.Scope} $scope
 * @param {!grrUi.core.reflectionService.ReflectionService} grrReflectionService
 * @ngInject
 */
const DictFormController = function(
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


/**
 * Converts given RDFValue object from RDFString to a more appropriate type,
 * if needed. If conversion is impossible, or value is not an RDFValue,
 * it's returned as-is.
 *
 * @param {Object|undefined} value Value to be converted.
 * @return {Object|undefined} Converted value.
 */
DictFormController.prototype.convertFromRDFString = function(value) {
  if (angular.isUndefined(value) ||
      value['type'] != 'RDFString') {
    return value;
  }

  value = angular.copy(value);
  var s = value['value'].trim();

  if (/^\d+$/.test(s)) {
    value['value'] = parseInt(s, 10);
    value['type'] = 'RDFInteger';
  } else if (/^0x[0-9a-fA-F]+$/.test(s)) {
    value['value'] = parseInt(s.substring(2), 16);
    value['type'] = 'RDFInteger';
  } else if (s.toLowerCase() == 'true') {
    value['value'] = true;
    value['type'] = 'RDFBool';
  } else if (s.toLowerCase() == 'false') {
    value['value'] = false;
    value['type'] = 'RDFBool';
  }

  return value;
};


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
      this.scope_.value.value[pair['key']] =
          this.convertFromRDFString(pair['value']);
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

          // This has to do with how Angular propagates changes. We have an
          // object that we edit that's passed inside the directive. And it's a
          // dictionary of random types. But in order to render the UI, etc we
          // have to convert it to a list of objects - it's much more
          // convenient.
          //
          // Then, given that we have 2 representations, we have to make sure
          // they're in sync. The way it's done is that every time internal
          // representation change, we update external one, and every time
          // external one changes, we update the internal one.
          //
          // To avoid infinite loop of change notifications we only update the
          // external representation if it has actually changed. This is why
          // the check is here. We say: "ok, if we take current value and
          // convert it to a proper type (RDFInteger or RDFBool), will it be
          // equal to the object in the data model? If yes - then don't touch
          // it, so that new change notification is not generated"
          if (!angular.equals(this.convertFromRDFString(pair['value']),
                              value)) {
            pair['value'] = value;
          }
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
exports.DictFormDirective = function() {
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
exports.DictFormDirective.directive_name = 'grrFormDict';


/**
 * Semantic types corresponding to this directive.
 *
 * @const
 * @export
 */
exports.DictFormDirective.semantic_types = ['dict', 'Dict'];
