'use strict';

goog.require('grrUi.config.binariesListDirective.sortBinaries');
goog.require('grrUi.config.module');
goog.require('grrUi.tests.module');

describe('grr-binaries-list directive', function() {

  describe('sortBinaries()', function() {
    var sortBinaries = grrUi.config.binariesListDirective.sortBinaries;

    it('adds correct metadata to binaries without slashes in path', function() {
      var binaries = sortBinaries([{
        value: {
          path: {
            value: "foo"
          }
        }
      }]);
      expect(binaries[0]['pathLen']).toBe(1);
      expect(binaries[0]['dirName']).toBe('');
      expect(binaries[0]['baseName']).toBe('foo');
    });

    it('adds correct metadata to binaries with slashes in path', function() {
      var binaries = sortBinaries([{
        value: {
          path: {
            value: "foo/bar/42"
          }
        }
      }]);
      expect(binaries[0]['pathLen']).toBe(3);
      expect(binaries[0]['dirName']).toBe('foo/bar');
      expect(binaries[0]['baseName']).toBe('42');
    });

    it('puts paths with more slashes first', function() {
      var binaries = sortBinaries([
        {
          value: {
            path: {
              value: "foo"
            }
          }
        },
        {
          value: {
            path: {
              value: "foo/bar"
            }
          }
        },
        {
        value: {
          path: {
            value: "foo/bar/42"
          }
        }
        }
      ]);

      expect(binaries[0]['value']['path']['value']).toBe('foo/bar/42');
      expect(binaries[1]['value']['path']['value']).toBe('foo/bar');
      expect(binaries[2]['value']['path']['value']).toBe('foo');
    });

    it('sorts paths with same number of slashes alphabetically', function() {
      var binaries = sortBinaries([
        {
          value: {
            path: {
              value: "foo/b"
            }
          }
        },
        {
          value: {
            path: {
              value: "foo/c"
            }
          }
        },
        {
        value: {
          path: {
            value: "foo/a"
          }
        }
        }
      ]);

      expect(binaries[0]['value']['path']['value']).toBe('foo/a');
      expect(binaries[1]['value']['path']['value']).toBe('foo/b');
      expect(binaries[2]['value']['path']['value']).toBe('foo/c');
    });
  });

  var $compile, $rootScope, $q, grrApiService;
  beforeEach(module('/static/angular-components/config/binaries-list.html'));
  beforeEach(module(grrUi.config.module.name));
  beforeEach(module(grrUi.tests.module.name));

  beforeEach(inject(function($injector) {
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
    $q = $injector.get('$q');
    grrApiService = $injector.get('grrApiService');
  }));

  var render = function(binaries, typeFilter) {
    $rootScope.binaries = binaries;
    $rootScope.typeFilter = typeFilter;

    var template = '<grr-binaries-list binaries="binaries" ' +
        'type-filter="{$ typeFilter $}" />';
    var element = $compile(template)($rootScope);
    $rootScope.$apply();

    return element;
  };

  it('triggers download when row is clicked', function() {
    var element = render([{
        value: {
          path: {
            value: "foo/bar"
          },
          type: {
            value: 'PYTHON_HACK'
          }
        }
    }], 'PYTHON_HACK');

    var deferred = $q.defer();
    spyOn(grrApiService, 'downloadFile').and.returnValue(deferred.promise);

    browserTrigger(element.find('tr:contains("foo")'), 'click');

    expect(grrApiService.downloadFile).toHaveBeenCalledWith(
        '/config/binaries/PYTHON_HACK/foo/bar');
  });
});
