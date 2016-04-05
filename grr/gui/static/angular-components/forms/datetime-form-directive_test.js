'use strict';

goog.require('grrUi.forms.module');
goog.require('grrUi.tests.browserTrigger');
goog.require('grrUi.tests.module');

var browserTrigger = grrUi.tests.browserTrigger;

describe('datetime form directive', function() {
  var $compile, $rootScope, value;

  beforeEach(module('/static/angular-components/forms/datetime-form.html'));
  beforeEach(module(grrUi.forms.module.name));
  beforeEach(module(grrUi.tests.module.name));

  beforeEach(inject(function($injector) {
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
  }));

  var renderTestTemplate = function(value) {
    $rootScope.value = value;

    var template = '<grr-form-datetime value="value" />';
    var element = $compile(template)($rootScope);
    $rootScope.$apply();

    return element;
  };

  it('shows nothing if time value is null', function() {
    var element = renderTestTemplate({
      type: 'RDFDatetime',
      value: null
    });
    expect(element.find('input').val()).toBe('');
  });

  it('shows correct date if time value is 0', function() {
    var element = renderTestTemplate({
      type: 'RDFDatetime',
      value: 0
    });
    expect(element.find('input').val()).toBe('1970-01-01 00:00');
  });

  it('shows nothing if time value is too big', function() {
    var element = renderTestTemplate({
      type: 'RDFDatetime',
      value: 9223372036854776000
    });
    expect(element.find('input').val()).toBe('');
  });

  it('sets value to null on incorrect input', function() {
    var value = {
      type: 'RDFDatetime',
      value: 0
    };
    var element = renderTestTemplate(value);
    element.find('input').val('a');
    browserTrigger(element.find('input'), 'change');

    expect(value.value).toBe(null);
  });

  it('shows warning on incorrect input', function() {
    var value = {
      type: 'RDFDatetime',
      value: 0
    };
    var element = renderTestTemplate(value);
    element.find('input').val('a');
    browserTrigger(element.find('input'), 'change');

    expect(element.text()).toContain('Expected format is');
  });

  it('correctly updates the value on correct input', function() {
    var value = {
      type: 'RDFDatetime',
      value: 0
    };
    var element = renderTestTemplate(value);
    element.find('input').val('1989-04-20 13:42');
    browserTrigger(element.find('input'), 'change');

    expect(value.value).toBe(609082920000000);
  });

  it('sets current date when "today" button is pressed', function() {
    var value = {
      type: 'RDFDatetime',
      value: 0
    };
    var baseTime = new Date(Date.UTC(1989, 4, 20));
    jasmine.clock().mockDate(baseTime);

    var element = renderTestTemplate(value);
    browserTrigger(element.find('button[name=Today]'), 'click');

    expect(value.value).toBe(611625600000000);
  });

});
