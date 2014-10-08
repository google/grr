'use strict';
(function() {
  var module = angular.module('grr.collectionTable.directive',
                              ['grr.aff4.service',
                               'grr.inject.directive']);

  module.directive('grrCollectionTable', function(grrAff4Service) {
    return {
      scope: {
        collectionUrn: '@',
        fetchTypeInfo: '@',
        transformItems: '&',
        pageSize: '=?'
      },
      restrict: 'E',
      transclude: true,
      templateUrl: 'static/angular-components/core/collection-table.html',
      compile: function(element, attrs) {
        // This seems to be a traditional way of assigning default values
        // to directive's attributes.
        if (!attrs.pageSize) {
          attrs.pageSize = '100';
        }
      },
      controller: function($scope, $element) {
        $scope.currentPage = 0;
        $scope.showLoading = true;

        $scope.filter = {
          // We need 'editedValue' and 'value' so that we don't apply
          // the filter every time a user types new character into
          // the filter edit box.
          editedValue: '',
          value: '',
          applied: false,
          finished: false
        };

        $scope.totalCount = undefined;

        // Updates visible page numbers (stored in $scope.pageNumbers)
        // according to the currently selected page and total number
        // of pages.
        var updatePagesNumbers = function() {
          $scope.pageNumbers = [];
          if ($scope.currentPage > 5) {
            $scope.pageNumbers.push(1);
            $scope.pageNumbers.push(-1);
            for (var i = $scope.currentPage - 4; i <= $scope.currentPage; ++i) {
              $scope.pageNumbers.push(i);
            }
          } else {
            for (var i = 1; i <= $scope.currentPage; ++i) {
              $scope.pageNumbers.push(i);
            }
          }

          if ($scope.currentPage + 5 >= $scope.totalPages) {
            for (var i = $scope.currentPage + 1; i <= $scope.totalPages; ++i) {
              $scope.pageNumbers.push(i);
            }
          } else {
            for (var i = $scope.currentPage + 1; i <= $scope.currentPage + 5;
                 ++i) {
              $scope.pageNumbers.push(i);
            }
            if ($scope.currentPage + 5 < $scope.totalPages) {
              $scope.pageNumbers.push(-1);
              $scope.pageNumbers.push($scope.totalPages);
            }
          }
        };

        // Fetches unfiltered collection elements and updates paging controls.
        // Paging controls are only shown when filter is not applied, as it's
        // hard to predict how many filtered collection elements we're going
        // to get.
        var fetchUnfilteredContent = function(withTotalCount) {
          $scope.showLoading = true;
          $scope.collectionItems = [];

          var params = {
            'offset': $scope.currentPage * $scope.pageSize,
            'count': $scope.pageSize,
            'with_total_count': withTotalCount
          };
          if ($scope.fetchTypeInfo) {
            params['with_type_info'] = true;
          }
          grrAff4Service.get($scope.collectionUrn, params).then(
              function(response) {
                $scope.showLoading = false;

                if (response.data.items === undefined) {
                  $scope.collectionItems = [];
                  $scope.totalCount = 0;
                } else {
                  $scope.collectionItems = response.data.items;
                  $scope.totalCount = response.data.total_count;
                }
                if ($scope.transformItems) {
                  $scope.transformItems({items: $scope.collectionItems});
                }

                if (withTotalCount) {
                  $scope.totalPages = Math.ceil(
                      $scope.totalCount / $scope.pageSize);
                }
                updatePagesNumbers();
              });
        };

        // This functions is called when user clicks on a 'Filter' button or
        // presses Enter in the filter edit box.
        $scope.applyFilter = function() {
          $scope.filter.value = $scope.filter.editedValue;
          $scope.filter.applied = ($scope.filter.value !== '');
          $scope.filter.finished = false;
          $scope.currentPage = 0;
          $scope.collectionItems = [];

          if ($scope.filter.applied) {
            $scope.fetchFiltered();
          } else {
            fetchUnfilteredContent(false);
          }
        };

        // Fetches filtered values and increments current page.
        $scope.fetchFiltered = function(fetchAll) {
          $scope.showLoading = true;

          var numElements = $scope.pageSize;
          if (fetchAll) {
            numElements = 1e6;
          }

          var params = {
            'offset': $scope.currentPage * $scope.pageSize,
            'count': numElements,
            'filter': $scope.filter.value
          };
          if ($scope.fetchTypeInfo) {
            params['with_type_info'] = true;
          }
          grrAff4Service.get($scope.collectionUrn, params).then(
              function(response) {
                $scope.showLoading = false;

                $scope.collectionItems = $scope.collectionItems.concat(
                    response.data.items);
                if ($scope.transformItems) {
                  $scope.transformItems({items: $scope.collectionItems});
                }

                if (response.data.items.length < numElements) {
                  $scope.filter.finished = true;
                }
              });
          $scope.currentPage += 1;
        };

        $scope.selectPage = function(pageNumber) {
          $scope.currentPage = pageNumber - 1;
          fetchUnfilteredContent(false);
        };

        $scope.prevPage = function() {
          if ($scope.currentPage > 0) {
            $scope.currentPage -= 1;
            fetchUnfilteredContent(false);
          }
        };

        $scope.nextPage = function() {
          if ($scope.currentPage < $scope.totalPages - 1) {
            $scope.currentPage += 1;
            fetchUnfilteredContent(false);
          }
        };

        // Fetch initial batch of data along with a total count of all the
        // elements in the collection.
        fetchUnfilteredContent(true);
      }
    };
  });
})();
