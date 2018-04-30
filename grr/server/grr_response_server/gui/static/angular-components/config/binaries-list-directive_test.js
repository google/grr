'use strict';

goog.module('grrUi.config.binariesListDirectiveTest');

const {browserTriggerEvent, testsModule} = goog.require('grrUi.tests');
const {configModule} = goog.require('grrUi.config.config');
const {sortBinaries} = goog.require('grrUi.config.binariesListDirective');


describe('grr-binaries-list directive', () => {
  describe('sortBinaries()', () => {

    it('adds correct metadata to binaries without slashes in path', () => {
      const binaries = sortBinaries([{
        value: {
          path: {
            value: 'foo',
          },
        },
      }]);
      expect(binaries[0]['pathLen']).toBe(1);
      expect(binaries[0]['dirName']).toBe('');
      expect(binaries[0]['baseName']).toBe('foo');
    });

    it('adds correct metadata to binaries with slashes in path', () => {
      const binaries = sortBinaries([{
        value: {
          path: {
            value: 'foo/bar/42',
          },
        },
      }]);
      expect(binaries[0]['pathLen']).toBe(3);
      expect(binaries[0]['dirName']).toBe('foo/bar');
      expect(binaries[0]['baseName']).toBe('42');
    });

    it('puts paths with more slashes first', () => {
      const binaries = sortBinaries([
        {
          value: {
            path: {
              value: 'foo',
            },
          },
        },
        {
          value: {
            path: {
              value: 'foo/bar',
            },
          },
        },
        {
          value: {
            path: {
              value: 'foo/bar/42',
            },
          },
        },
      ]);

      expect(binaries[0]['value']['path']['value']).toBe('foo/bar/42');
      expect(binaries[1]['value']['path']['value']).toBe('foo/bar');
      expect(binaries[2]['value']['path']['value']).toBe('foo');
    });

    it('sorts paths with same number of slashes alphabetically', () => {
      const binaries = sortBinaries([
        {
          value: {
            path: {
              value: 'foo/b',
            },
          },
        },
        {
          value: {
            path: {
              value: 'foo/c',
            },
          },
        },
        {
          value: {
            path: {
              value: 'foo/a',
            },
          },
        },
      ]);

      expect(binaries[0]['value']['path']['value']).toBe('foo/a');
      expect(binaries[1]['value']['path']['value']).toBe('foo/b');
      expect(binaries[2]['value']['path']['value']).toBe('foo/c');
    });
  });

  let $compile;
  let $q;
  let $rootScope;
  let grrApiService;

  beforeEach(module('/static/angular-components/config/binaries-list.html'));
  beforeEach(module(configModule.name));
  beforeEach(module(testsModule.name));

  beforeEach(inject(($injector) => {
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
    $q = $injector.get('$q');
    grrApiService = $injector.get('grrApiService');
  }));

  const render = (binaries, typeFilter) => {
    $rootScope.binaries = binaries;
    $rootScope.typeFilter = typeFilter;

    const template = '<grr-binaries-list binaries="binaries" ' +
        'type-filter="{$ typeFilter $}" />';
    const element = $compile(template)($rootScope);
    $rootScope.$apply();

    return element;
  };

  it('triggers download when row is clicked', () => {
    const element = render(
        [{
          value: {
            path: {
              value: 'foo/bar',
            },
            type: {
              value: 'PYTHON_HACK',
            },
          },
        }],
        'PYTHON_HACK');

    const deferred = $q.defer();
    spyOn(grrApiService, 'downloadFile').and.returnValue(deferred.promise);

    browserTriggerEvent(element.find('tr:contains("foo")'), 'click');

    expect(grrApiService.downloadFile).toHaveBeenCalledWith(
        '/config/binaries-blobs/PYTHON_HACK/foo/bar');
  });
});


exports = {};
