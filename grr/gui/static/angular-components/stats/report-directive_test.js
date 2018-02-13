'use strict';

goog.module('grrUi.stats.reportDirectiveTest');

const {statsModule} = goog.require('grrUi.stats.stats');
const {stripTypeInfo} = goog.require('grrUi.core.apiService');
const {stubDirective, testsModule} = goog.require('grrUi.tests');


describe('report directive', () => {
  let $compile;
  let $q;
  let $rootScope;
  let grrApiService;
  let grrTimeService;


  beforeEach(module(
      '/static/angular-components/stats/report.html'));
  beforeEach(module(statsModule.name));
  beforeEach(module(testsModule.name));

  stubDirective('grrFormClientLabel');
  stubDirective('grrFormTimerange');
  stubDirective('grrChart');

  beforeEach(inject(($injector) => {
    $q = $injector.get('$q');
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
    grrApiService = $injector.get('grrApiService');
    grrTimeService = $injector.get('grrTimeService');

    let clock = grrTimeService.getCurrentTimeMs();
    grrTimeService.getCurrentTimeMs = (() => {
      clock += 42;
      return clock;
    });
  }));

  const renderTestTemplate = (name) => {
    $rootScope.name = name;

    const template = '<grr-report name="name">' +
        '</grr-report>';
    const element = $compile(template)($rootScope);
    $rootScope.$apply();

    return element;
  };

  // mockGrrApiService mocks the `stats/reports' and `stats/reports/*' calls.
  //
  // The mocked `stats/reports' handler will return a list of report descriptors
  // used in this test.
  //
  // The mocked `stats/reports/*' call handler will expect deferredWork[path]
  // to be initialized with an angular promise and will pretend to do false
  // work until the corresponding promise is resolved.
  const mockGrrApiService = () => {
    const deferredWork = {};

    spyOn(grrApiService, 'get').and.callFake((path) => {
      const deferred = $q.defer();
      const promise = deferred.promise;

      if (path === 'stats/reports') {
        const response = {
          'reports': [
            {
              'type': 'ApiReport',
              'value': {
                'desc': {
                  'type': 'ApiReportDescriptor',
                  'value': {
                    'name': {
                      'type': 'unicode',
                      'value': 'FooReportPlugin',
                    },
                    'summary': {
                      'type': 'unicode',
                      'value': 'Foo\'s summary.',
                    },
                    'type': {
                      'type': 'EnumNamedValue',
                      'value': 'FOO_TYPE',
                    },
                    'requires_time_range': {
                      'type': 'RDFBool',
                      'value': false,
                    },
                    'title': {'type': 'unicode', 'value': 'Foo Report'},
                  },
                },
              },
            },
            {
              'type': 'ApiReport',
              'value': {
                'desc': {
                  'type': 'ApiReportDescriptor',
                  'value': {
                    'name': {
                      'type': 'unicode',
                      'value': 'BarReportPlugin',
                    },
                    'summary': {
                      'type': 'unicode',
                      'value': 'Bar\'s summary.',
                    },
                    'type': {
                      'type': 'EnumNamedValue',
                      'value': 'BAR_TYPE',
                    },
                    'requires_time_range': {
                      'type': 'RDFBool',
                      'value': false,
                    },
                    'title': {'type': 'unicode', 'value': 'Bar Report'},
                  },
                },
              },
            }
          ],
        };

        deferred.resolve({ data: response });
      }
      else {
        const response = {
          data: {
            data: {
              value: {
                representation_type: {
                  value: 'STACK_CHART',
                },
                stack_chart: {
                  value: {
                    data: [
                      {
                        value: {
                          label: path,
                          points: [],
                        },
                      },
                    ],
                  },
                },
              },
            },
          },
        };

        // Do some fake work and respond.
        deferredWork[path].promise.then(() => {
          deferred.resolve({ data: response });
        });
      }

      return promise;
    });

    return deferredWork;
  };

  it('drops responses to old requests', () => {
    const deferredWork = mockGrrApiService();
    deferredWork['stats/reports/FooReportPlugin'] = $q.defer();
    deferredWork['stats/reports/BarReportPlugin'] = $q.defer();

    const element = renderTestTemplate('FooReportPlugin');

    // Change the report description while the other one's still loading.
    $rootScope.name = 'BarReportPlugin';
    $rootScope.$apply();

    // The chart should still be loading.
    expect(element.find('grr-chart').length).toBe(0);

    // Resolve the old request.
    deferredWork['stats/reports/FooReportPlugin'].resolve();
    $rootScope.$apply();

    // The chart should still be loading.
    expect(element.find('grr-chart').length).toBe(0);

    // Resolve the new request.
    deferredWork['stats/reports/BarReportPlugin'].resolve();
    $rootScope.$apply();

    // The chart should now be loaded.
    const chart = element.find('grr-chart');
    expect(chart.length).toBe(1);

    const attribute = chart.attr('typed-data');
    const typedData = chart.scope().$eval(attribute);
    const data = stripTypeInfo(typedData['data']);

    expect(data['stack_chart']['data'][0]['label']).toBe(
        'stats/reports/BarReportPlugin');

    expect(JSON.stringify(typedData)).not.toContain('FooReportPlugin');
  });
});


exports = {};
