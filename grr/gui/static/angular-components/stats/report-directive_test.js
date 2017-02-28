'use strict';

goog.require('grrUi.core.apiService.stripTypeInfo');
goog.require('grrUi.stats.module');
goog.require('grrUi.tests.module');
goog.require('grrUi.tests.stubDirective');

describe('report directive', function() {
  var $q, $compile, $rootScope, grrApiService, grrTimeService;

  beforeEach(module(
      '/static/angular-components/stats/report.html'));
  beforeEach(module(grrUi.stats.module.name));
  beforeEach(module(grrUi.tests.module.name));

  grrUi.tests.stubDirective('grrFormClientLabel');
  grrUi.tests.stubDirective('grrFormTimerange');
  grrUi.tests.stubDirective('grrChart');

  beforeEach(inject(function($injector) {
    $q = $injector.get('$q');
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
    grrApiService = $injector.get('grrApiService');
    grrTimeService = $injector.get('grrTimeService');

    var clock = grrTimeService.getCurrentTimeMs();
    grrTimeService.getCurrentTimeMs = function() {
      clock += 42;
      return clock;
    };
  }));

  var renderTestTemplate = function(name) {
    $rootScope.name = name;

    var template = '<grr-report name="name">' +
                   '</grr-report>';
    var element = $compile(template)($rootScope);
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
  var mockGrrApiService = function() {
    var deferredWork = {};

    spyOn(grrApiService, 'get').and.callFake(function(path) {
      var deferred = $q.defer();
      var promise = deferred.promise;

      if (path === 'stats/reports') {
        var response = {
          'reports': [{
            'type': 'ApiReport',
            'value': {
              'desc': {
                'type': 'ApiReportDescriptor',
                'value': {
                  'name': {
                    'type': 'unicode',
                    'value': 'FooReportPlugin'
                  },
                  'summary': {
                    'type': 'unicode',
                    'value': 'Foo\'s summary.'
                  },
                  'type': {
                    'type': 'EnumNamedValue',
                    'value': 'FOO_TYPE'
                  },
                  'requires_time_range': {
                    'type': 'RDFBool',
                    'value': false
                  },
                  'title': {
                    'type': 'unicode',
                    'value': 'Foo Report'}
                }
              }
            }
          }, {
            'type': 'ApiReport',
            'value': {
              'desc': {
                'type': 'ApiReportDescriptor',
                'value': {
                  'name': {
                    'type': 'unicode',
                    'value': 'BarReportPlugin'
                  },
                  'summary': {
                    'type': 'unicode',
                    'value': 'Bar\'s summary.'
                  },
                  'type': {
                    'type': 'EnumNamedValue',
                    'value': 'BAR_TYPE'
                  },
                  'requires_time_range': {
                    'type': 'RDFBool',
                    'value': false
                  },
                  'title': {
                    'type': 'unicode',
                    'value': 'Bar Report'}
                }
              }
            }
          }]
        };

        deferred.resolve({ data: response });
      }
      else {
        var response = {
          data: {
            data: {
              value: {
                representation_type: {
                  value: 'STACK_CHART'
                },
                stack_chart: {
                  value: {
                    data: [
                      {
                        value: {
                          label: path,
                          points: []
                        }
                      }
                    ]
                  }
                }
              }
            }
          }
        };

        // Do some fake work and respond.
        deferredWork[path].promise.then(function() {
          deferred.resolve({ data: response });
        });
      }

      return promise;
    });

    return deferredWork;
  };

  it('drops responses to old requests', function() {
    var deferredWork = mockGrrApiService();
    deferredWork['stats/reports/FooReportPlugin'] = $q.defer();
    deferredWork['stats/reports/BarReportPlugin'] = $q.defer();

    var element = renderTestTemplate('FooReportPlugin');

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
    var chart = element.find('grr-chart');
    expect(chart.length).toBe(1);

    var attribute = chart.attr('typed-data');
    var typedData = chart.scope().$eval(attribute);
    var data = grrUi.core.apiService.stripTypeInfo(typedData['data']);

    expect(data['stack_chart']['data'][0]['label']).toBe(
        'stats/reports/BarReportPlugin');

    expect(JSON.stringify(typedData)).not.toContain('FooReportPlugin');
  });
});
