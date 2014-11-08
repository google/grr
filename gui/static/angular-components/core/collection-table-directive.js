'use strict';

goog.provide('grrUi.core.collectionTableDirective.CollectionTableDirective');

goog.scope(function() {



/**
 * Controller for the CollectionTableDirective.
 *
 * @param {angular.Scope} $scope
 * @param {grrUi.core.aff4Service.Aff4Service} grrAff4Service
 * @constructor
 * @ngInject
 * @export
 */
var CollectionTableController = function($scope, grrAff4Service) {
  /** @private {angular.Scope} */
  this.scope_ = $scope;

  /** @private {grrUi.core.aff4Service.Aff4Service} */
  this.grrAff4Service_ = grrAff4Service;

  this.scope_.currentPage = 0;
  this.scope_.showLoading = true;

  this.scope_.filter = {
    // We need 'editedValue' and 'value' so that we don't apply
    // the filter every time a user types new character into
    // the filter edit box.
    editedValue: '',
    value: '',
    applied: false,
    finished: false
  };

  this.scope_.totalCount = undefined;

  // Fetch initial batch of data along with a total count of all the
  // elements in the collection.
  this.fetchUnfilteredContent_(true);
};


/**
 * Fetches unfiltered records from AFF4 service.
 *
 * @param {boolean} withTotalCount If True, total count of elements in the
 *                                 collection will be fetched.
 * @private
 */
CollectionTableController.prototype.fetchUnfilteredContent_ = function(
    withTotalCount) {
  this.scope_.showLoading = true;
  this.scope_.collectionItems = [];

  var params = {
    'offset': this.scope_.currentPage * this.scope_.pageSize,
    'count': this.scope_.pageSize,
    'with_total_count': withTotalCount
  };
  if (this.scope_.fetchTypeInfo) {
    params['with_type_info'] = true;
  }

  var self = this;
  this.grrAff4Service_.get(this.scope_.collectionUrn, params).then(
      function(response) {
        self.scope_.showLoading = false;

        if (response['data']['items'] === undefined) {
          self.scope_.collectionItems = [];
          self.scope_.totalCount = 0;
        } else {
          self.scope_.collectionItems = response['data']['items'];
          self.scope_.totalCount = response['data']['total_count'];
        }
        if (self.scope_.transformItems) {
          self.scope_.transformItems({items: self.scope_.collectionItems});
        }
      });
};


/**
 * Updates filter-related UI variables and fetches filtered records from AFF4
 * service.
 */
CollectionTableController.prototype.applyFilter = function() {
  this.scope_.filter.value = this.scope_.filter.editedValue;
  this.scope_.filter.applied = (this.scope_.filter.value !== '');
  this.scope_.filter.finished = false;
  this.scope_.currentPage = 0;
  this.scope_.collectionItems = [];

  if (this.scope_.filter.applied) {
    this.fetchFiltered();
  } else {
    this.fetchUnfilteredContent_(false);
  }
};


/**
 * Fetches filtered records from AFF4 service.
 *
 * @param {boolean} fetchAll If True, fetch all the elements.
 */
CollectionTableController.prototype.fetchFiltered = function(fetchAll) {
  this.scope_.showLoading = true;

  var numElements = this.scope_.pageSize;
  if (fetchAll) {
    numElements = 1e6;
  }

  var params = {
    'offset': this.scope_.currentPage * this.scope_.pageSize,
    'count': numElements,
    'filter': this.scope_.filter.value
  };

  if (this.scope_.fetchTypeInfo) {
    params['with_type_info'] = true;
  }

  var self = this;
  this.grrAff4Service_.get(this.scope_.collectionUrn, params).then(
      function(response) {
        self.scope_.showLoading = false;

        self.scope_.collectionItems = self.scope_.collectionItems.concat(
            response.data.items);
        if (self.scope_.transformItems) {
          self.scope_.transformItems({items: self.scope_.collectionItems});
        }

        if (response.data.items.length < numElements) {
          self.scope_.filter.finished = true;
        }
      });
  this.scope_.currentPage += 1;
};


/**
 * Change currently shown page and fetches appropriate records from AFF4
 * service.
 *
 * @param {number} pageNumber Page number.
 */
CollectionTableController.prototype.selectPage = function(pageNumber) {
  this.scope_.currentPage = pageNumber - 1;
  this.fetchUnfilteredContent_(false);
};



/**
 * CollectionTableDirective displays given RDFValueCollection with a
 * user-supplied template applied to every record.
 *
 * @constructor
 * @ngInject
 * @export
 */
grrUi.core.collectionTableDirective.CollectionTableDirective = function() {
  return {
    scope: {
      collectionUrn: '@',
      fetchTypeInfo: '@',
      transformItems: '&',
      pageSize: '=?'
    },
    restrict: 'E',
    transclude: true,
    templateUrl: '/static/angular-components/core/collection-table.html',
    compile: function(element, attrs) {
      // This seems to be a traditional way of assigning default values
      // to directive's attributes.
      if (!attrs.pageSize) {
        attrs.pageSize = '100';
      }
    },
    controller: CollectionTableController,
    controllerAs: 'controller'
  };
};


/**
 * Name of the directive as regisered in Angular.
 */
grrUi.core.collectionTableDirective.CollectionTableDirective.
    directive_name = 'grrCollectionTable';

});  // goog.scope
