'use strict';

goog.require('grrUi.forms.module');
goog.require('grrUi.tests.module');
goog.require('grrUi.tests.stubDirective');


describe('timerange form directive', function() {
  var $compile, $rootScope, value, $q, grrReflectionService;

  beforeEach(module('/static/angular-components/forms/timerange-form.html'));
  beforeEach(module(grrUi.forms.module.name));
  beforeEach(module(grrUi.tests.module.name));

  grrUi.tests.stubDirective('grrFormValue');

  beforeEach(inject(function($injector) {
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
    $q = $injector.get('$q');
    grrReflectionService = $injector.get('grrReflectionService');

    spyOn(grrReflectionService, 'getRDFValueDescriptor').and.callFake(
        function(valueType) {
          var deferred = $q.defer();

          if (valueType === 'RDFDatetime') {
            deferred.resolve({
              default: {
                type: 'RDFDatetime',
                value: 0
              }
            });
          } else if (valueType === 'Duration') {
            deferred.resolve({
              default: {
                type: 'Duration',
                value: 0
              }
            });
          }

          return deferred.promise;
        });
  }));

  var renderTestTemplate = function(
      startTimeSecs, durationSecs, startTimeLabel, durationLabel) {
    $rootScope.startTimeSecs = startTimeSecs;
    $rootScope.durationSecs = durationSecs;

    if (angular.isDefined(startTimeLabel)) {
      $rootScope.startTimeLabel = startTimeLabel;
    }

    if (angular.isDefined(durationLabel)) {
      $rootScope.durationLabel = durationLabel;
    }

    var template = '<grr-form-timerange ' +
                       'start-time-secs="startTimeSecs" ' +
                       'duration-secs="durationSecs" ' +

                       (angular.isDefined(startTimeLabel) ?
                       'start-time-label="startTimeLabel" ' : '') +

                       (angular.isDefined(durationLabel) ?
                       'duration-label="durationLabel" ' : '') +
                   '></grr-form-timerange>';
    var element = $compile(template)($rootScope);
    $rootScope.$apply();

    return element;
  };

  it('shows the given scope params initially', function() {
    var element = renderTestTemplate(123, 456);

    var directive = element.find('grr-form-value:nth(0)');
    expect(directive.scope().$eval(directive.attr('value'))).toEqual(
        {
          type: 'RDFDatetime',
          value: 123000000  // This should be converted to μs.
        });

    directive = element.find('grr-form-value:nth(1)');
    expect(directive.scope().$eval(directive.attr('value'))).toEqual(
        {
          type: 'Duration',
          value: 456
        });
  });

  it('shows default labels by default', function() {
    var element = renderTestTemplate(123, 456);

    expect(element.find('label:nth(0)').text()).toBe('Time range start time');
    expect(element.find('label:nth(1)').text()).toBe('Time range duration');
  });

  it('shows custom labels if given', function() {
    var element = renderTestTemplate(
        123, 456, 'Custom start time label', 'Custom duration label');

    expect(element.find('label:nth(0)').text()).toBe('Custom start time label');
    expect(element.find('label:nth(1)').text()).toBe('Custom duration label');
  });

  it('forwards changed values to parent scope', function() {
    var element = renderTestTemplate(123, 456);

    var directive = element.find('grr-form-value:nth(0)');
    directive.scope().$eval(directive.attr('value') + '.value = 321000000');

    directive = element.find('grr-form-value:nth(1)');
    directive.scope().$eval(directive.attr('value') + '.value = 654');

    $rootScope.$apply();

    expect(element.scope().$eval(element.attr('start-time-secs'))).toEqual(321);
    expect(element.scope().$eval(element.attr('duration-secs'))).toEqual(654);
  });

});
