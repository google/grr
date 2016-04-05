'use strict';

goog.require('grrUi.semantic.module');
goog.require('grrUi.tests.module');

describe('timestamp seconds directive', function() {
  var MILLI_IN_UNIT = 1000;
  var MINUTE = 60;
  var $compile, $rootScope;

  beforeEach(module(grrUi.semantic.module.name));
  beforeEach(module(grrUi.tests.module.name));

  beforeEach(inject(function($injector) {
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
  }));

  var renderTestTemplate = function(value) {
    $rootScope.value = value;

    var template = '<grr-timestamp-seconds value="value" />';
    var element = $compile(template)($rootScope);
    $rootScope.$apply();

    return element;
  };

  it('does not show anything when value is undefined', function() {
    var element = renderTestTemplate(undefined);
    expect(element.text().trim()).toBe('');
  });

  it('does not show anything when value is null', function() {
    var element = renderTestTemplate(null);
    expect(element.text().trim()).toBe('-');
  });

  it('shows "-" when value is 0', function() {
    var element = renderTestTemplate(0);
    expect(element.text().trim()).toBe('-');
  });

  it('shows integer value', function() {
    var element = renderTestTemplate(42);
    expect(element.text()).toContain('1970-01-01 00:00:42');
  });

  it('shows value with type information', function() {
    var timestamp = {
      'mro': ['RDFDatetimeSeconds', 'RDFDatetime', 'RDFInteger', 'RDFString', 'RDFBytes',
              'RDFValue', 'object'],
      'value': 42,
      'age': 0,
      'type': 'RDFDatetimeSeconds'
    };
    var element = renderTestTemplate(timestamp);
    expect(element.text()).toContain('1970-01-01 00:00:42');
  });

  it('includes a human-readable diff when hovered', function() {
    function assertTimestampRendersDiff(timestamp, diff) {
      var element = renderTestTemplate(timestamp);
      var span = $(element).find('span');

      // Simulate a mouseenter event on the span.
      // Doing a mouseenter on the parent directive would not work, as the
      // events bubble outwards towards the parent hierarchy, and the span
      // would not see // this event, so the controller wouldn't capture it.
      browserTrigger($(element).find('span'), 'mouseenter');

      expect(span.attr('title')).toContain(diff);
    }

    var now = (new Date() - 0) / MILLI_IN_UNIT;

    // ignore very small differences from the current time
    assertTimestampRendersDiff(now, 'now');
  });
});
