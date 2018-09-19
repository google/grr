goog.module('grrUi.forms.semanticProtoFormDirective');
goog.module.declareLegacyNamespace();



/**
 * Controller for SemanticProtoFormDirective.
 *
 * @constructor
 * @param {!angular.Scope} $scope
 * @param {!angular.Attributes} $attrs
 * @param {!grrUi.core.reflectionService.ReflectionService} grrReflectionService
 * @ngInject
 */
const SemanticProtoFormController = function(
    $scope, $attrs, grrReflectionService) {
  /** @private {!angular.Scope} */
  this.scope_ = $scope;

  /** @private {!grrUi.core.reflectionService.ReflectionService} */
  this.grrReflectionService_ = grrReflectionService;

  /** @type {boolean} */
  this.advancedShown = false;

  /** @type {boolean} */
  this.hasAdvancedFields = false;

  /** @type {boolean} */
  this.expanded = false;

  /** @type {?Object|undefined} */
  this.editedValue;

  /** @type {?Object|undefined} */
  this.lastAssignedScopeValue_;

  if (angular.isDefined($attrs['hiddenFields']) &&
      angular.isDefined($attrs['visibleFields'])) {
    throw new Error('Either hidden-fields or visible-fields attribute may ' +
                    'be specified, not both.');
  }

  this.scope_.$watch('value',
                     this.onValueChange_.bind(this),
                     true);
  this.scope_.$watch('controller.editedValue.value',
                     this.onEditedValueChange_.bind(this),
                     true);

  this.boundNotExplicitlyHiddenFields =
      this.notExplicitlyHiddenFields_.bind(this);

};


/**
 * Filter function that returns true if the field wasn't explicitly mentioned
 * in 'hidden-fields' directive's argument.
 *
 * @param {string} field Name of a field.
 * @param {number=} opt_index Index of the field name in the names list
 *                            (optional).
 * @return {boolean} True if the field is not hidden, false otherwise.
 * @private
 */
SemanticProtoFormController.prototype.notExplicitlyHiddenFields_ = function(
    field, opt_index) {
  if (angular.isDefined(this.scope_['hiddenFields'])) {
    return this.scope_['hiddenFields'].indexOf(field['name']) == -1;
  } else if (angular.isDefined(this.scope_['visibleFields'])) {
    return this.scope_['visibleFields'].indexOf(field['name']) != -1;
  } else {
    return true;
  }
};

/**
 * Predicate that returns true only for regular (non-hidden, non-advanced)
 * fields.
 *
 * @param {Object} field Descriptor field to check.
 * @param {Number} index Descriptor field index.
 * @return {boolean}
 * @export
 */
SemanticProtoFormController.prototype.regularFieldsOnly = function(
    field, index) {
  return angular.isUndefined(field['labels']) ||
      field['labels'].indexOf('HIDDEN') == -1 &&
      field['labels'].indexOf('ADVANCED') == -1;
};


/**
 * Predicate that returns true only for advanced (and non-hidden) fields.
 *
 * @param {Object} field Descriptor field to check.
 * @param {Number} index Descriptor field index.
 * @return {boolean}
 * @export
 */
SemanticProtoFormController.prototype.advancedFieldsOnly = function(
    field, index) {
  return angular.isDefined(field['labels']) &&
      field['labels'].indexOf('HIDDEN') == -1 &&
      field['labels'].indexOf('ADVANCED') != -1;
};


/**
 * Handles changes of the value type.
 *
 * @param {?string} newValue
 * @param {?string} oldValue
 * @private
 */
SemanticProtoFormController.prototype.onValueChange_ = function(
    newValue, oldValue) {
  if (angular.isUndefined(newValue)) {
    this.descriptors = undefined;
    this.valueDescriptor = undefined;
    this.editedValue = undefined;
    return;
  }

  /**
   * onEditedValueChange_ updates scope['value']. In order not to
   * trigger an endless onEditedValueChange_<->onValueChange_ loop,
   * onEditedValueChange_ stores the last updated version of
   * scope['value'] in lastAssignedScopeValue_. By comparing
   * this stored value to the incoming newValue we can check
   * if this onValueChange_ call is triggered by the changes
   * done in onEditedValueChange_ and therefore should do nothing.
   *
   * If this onValueChange_ call has nothing to do with a change made
   * in onEditedValueChange_, it means that the scope['value']
   * binding was changed from the outside and therefore we
   * should rerender the UI to get everythign updated.
   *
   * NOTE: current implementation assumes that such external changes
   * are not done too often since every onDescriptorsFetched_ call
   * is expensive. I.e. we shouldn't have 2 forms on the same page
   * editing same object in parallel - it would work, but will eat
   * quite a lot of CPU.
   */
  if (angular.isDefined(this.lastAssignedScopeValue_) &&
      angular.isDefined(newValue) &&
      this.lastAssignedScopeValue_['type'] === newValue['type']) {
    /**
     * Find a field that:
     * a) Does not have a HIDDEN label.
     * b) Is not considered hidden due to hiddenFields/visibleFields directive
     *    bindings.
     * c) Has a different value in lastAssignedScopeValue_ and "value" directive
     *    binding.
     *
     * If such field is found, it means that the scope's "value" binding got
     * updated from the outside. This should trigger this.onDescriptorsFetched_
     * call.
     *
     * This custom comparison logic is needed in order not to trigger form
     * updates when hidden fields are being updated.
     */
    const updatedField = this.valueDescriptor['fields'].find((field) => {
      const hasHiddenLabel = (field['labels'] &&
                              field['labels'].indexOf('HIDDEN') != -1);
      return (!hasHiddenLabel &&
              this.notExplicitlyHiddenFields_(field) &&
              !angular.equals(
                  newValue['value'][field['name']],
                  this.lastAssignedScopeValue_['value'][field['name']]));
    });

    if (updatedField === undefined) {
      return;
    }
  }

  this.grrReflectionService_.getRDFValueDescriptor(
      this.scope_['value']['type'], true).then(
          this.onDescriptorsFetched_.bind(this));
};

/**
 * Handles changes in the editedValue variable. editedValue contains
 * actual data that are being edited by the form controls. When it changes,
 * the changes are propagated to the main 'value' binding. This is done
 * in order not to set all the fields to their default values in 'value':
 * editedValue is initialized with all the default values, but 'value'
 * only changes when user actually inputs something.
 *
 * @param {Object} newValue
 * @param {Object} oldValue
 * @private
 */
SemanticProtoFormController.prototype.onEditedValueChange_ = function(
    newValue, oldValue) {
  if (angular.isDefined(newValue)) {
    /**
     * Only apply changes to scope_['value'] if oldValue is defined, i.e.
     * if the changes were actually made by the user editing the form.
     * oldValue === null means that editedValue was just initialized
     * from scope_['value'], so no need to migrate any changes.
     */
    if (angular.isDefined(oldValue)) {
      /**
       * It's ok to traverse only the keys of newValue, because keys can't be
       * removed, only added.
       */
      angular.forEach(newValue, function(value, key) {
        if (!angular.equals(oldValue[key], newValue[key])) {
          this.scope_['value']['value'][key] = angular.copy(value);
        }
      }.bind(this));
    }

    /**
     *  Remove the fields that are equal to their default values (by
     *  "default" we mean either field default or value default).
     */
    angular.forEach(this.valueDescriptor['fields'], function(field) {
      if (this.notExplicitlyHiddenFields_(field)) {
        if (field['type'] &&
            angular.equals(this.scope_['value']['value'][field['name']],
                           this.descriptors[field['type']]['default']) &&
            /**
             * If the field has a per-field special default value that's
             * different from the field type's default value, we shouldn't erase
             * the field (so that when the form is submitted, the special
             * default values gets sent to the server).
             *
             * For example, if the field is integer and has an explicit default
             * value 0, then the field will be erased if its current value is 0.
             *
             * But if the field is integer and has an explicit default of 42,
             * then it won't get erased when its current value is 42 (nor will
             * it get erased when its default is 0).
             */
            (angular.isUndefined(field['default']) ||
             angular.equals(field['default'],
                            this.descriptors[field['type']]['default']))) {
          delete this.scope_['value']['value'][field['name']];
        }
      }
    }.bind(this));

    this.lastAssignedScopeValue_ = angular.copy(this.scope_['value']);
  }
};


/**
 * Handles fetched reflection data.
 *
 * @param {!Object<string, Object>} descriptors
 * @private
 */
SemanticProtoFormController.prototype.onDescriptorsFetched_ = function(
    descriptors) {
  this.descriptors = descriptors;
  this.valueDescriptor = angular.copy(
      descriptors[this.scope_['value']['type']]);

  if (angular.isUndefined(this.editedValue)) {
    this.editedValue = angular.copy(this.scope_['value']);
  }
  if (angular.isUndefined(this.editedValue['value'])) {
    this.editedValue.value = {};
  }

  angular.forEach(this.valueDescriptor['fields'], function(field) {
    if (angular.isDefined(field['labels'])) {
      if (field['labels'].indexOf('HIDDEN') != -1) {
        return;
      }

      if (field['labels'].indexOf('ADVANCED') != -1) {
        this.hasAdvancedFields = true;
      }
    }

    // Determine appropriate default value for this field.
    let defaultFieldValue = undefined;
    // We can't initialize dynamic fields in any way - we don't know which
    // type they should be.
    if (!field['dynamic']) {
      if (field['repeated']) {
        field['depth'] = 0;
        defaultFieldValue = [];
      } else {
        field['depth'] = (this.scope_.$eval('metadata.depth') || 0) + 1;
        if (angular.isDefined(field['default'])) {
          defaultFieldValue = angular.copy(field['default']);
        } else {
          defaultFieldValue = angular.copy(
              descriptors[field['type']]['default']);
        }
      }
    }

    // Copy each field only when its value has actually changed from what
    // we currently have. This prevents unnecessary UI updates.
    const scopeValueContent = this.scope_['value']['value'];
    const editedValueConent = this.editedValue['value'];

    const fieldName = field['name'];
    const fieldValueChanged = !angular.equals(
        scopeValueContent[fieldName],
        editedValueConent[fieldName]);
    // Update the field only if its value has changed. Ignore cases when
    // the field should have a default value (since the source field is
    // undefined) and already has it, meaning that we shouldn't assign
    // anything.
    if (fieldValueChanged &&
        !(scopeValueContent[fieldName] === undefined &&
          angular.equals(editedValueConent[fieldName],defaultFieldValue))) {
      editedValueConent[fieldName] = angular.copy(scopeValueContent[fieldName]);
    }

    // Now initialize unset fields with default values, if needed and possible.
    if (defaultFieldValue !== undefined &&
        angular.isUndefined(editedValueConent[fieldName])) {
      editedValueConent[fieldName] = defaultFieldValue;
    }

  }.bind(this));

  this.lastAssignedScopeValue_ = angular.copy(this.scope_['value']);
};

/**
 * SemanticProtoFormDirective renders a form corresponding to a given
 * RDFProtoStruct.
 *
 * @return {!angular.Directive} Directive definition object.
 */
exports.SemanticProtoFormDirective = function() {
  return {
    scope: {
      value: '=',
      metadata: '=?',
      hiddenFields: '=?',
      visibleFields: '=?'
    },
    restrict: 'E',
    templateUrl: '/static/angular-components/forms/semantic-proto-form.html',
    controller: SemanticProtoFormController,
    controllerAs: 'controller'
  };
};


/**
 * Name of the directive in Angular.
 *
 * @const
 * @export
 */
exports.SemanticProtoFormDirective.directive_name = 'grrFormProto';


/**
 * Semantic type corresponding to this directive.
 *
 * @const
 * @export
 */
exports.SemanticProtoFormDirective.semantic_type = 'RDFProtoStruct';
