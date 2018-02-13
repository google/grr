'use strict';

goog.module('grrUi.forms.datetimeFormDirectiveTest');

const {browserTriggerEvent, testsModule} = goog.require('grrUi.tests');
const {formsModule} = goog.require('grrUi.forms.forms');


describe('datetime form directive', () => {
  let $compile;
  let $rootScope;


  beforeEach(module('/static/angular-components/forms/datetime-form.html'));
  beforeEach(module(formsModule.name));
  beforeEach(module(testsModule.name));

  beforeEach(inject(($injector) => {
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
  }));

  const renderTestTemplate = (value) => {
    $rootScope.value = value;

    const template = '<grr-form-datetime value="value" />';
    const element = $compile(template)($rootScope);
    $rootScope.$apply();

    return element;
  };

  it('shows nothing if time value is null', () => {
    const element = renderTestTemplate({
      type: 'RDFDatetime',
      value: null,
    });
    expect(element.find('input').val()).toBe('');
  });

  it('shows correct date if time value is 0', () => {
    const element = renderTestTemplate({
      type: 'RDFDatetime',
      value: 0,
    });
    expect(element.find('input').val()).toBe('1970-01-01 00:00');
  });

  it('shows nothing if time value is too big', () => {
    const element = renderTestTemplate({
      type: 'RDFDatetime',
      value: 9223372036854776000,
    });
    expect(element.find('input').val()).toBe('');
  });

  it('sets value to null on incorrect input', () => {
    const value = {
      type: 'RDFDatetime',
      value: 0,
    };
    const element = renderTestTemplate(value);
    element.find('input').val('a');
    browserTriggerEvent(element.find('input'), 'change');

    expect(value.value).toBe(null);
  });

  it('shows warning on incorrect input', () => {
    const value = {
      type: 'RDFDatetime',
      value: 0,
    };
    const element = renderTestTemplate(value);
    element.find('input').val('a');
    browserTriggerEvent(element.find('input'), 'change');

    expect(element.text()).toContain('Expected format is');
  });

  it('correctly updates the value on correct input', () => {
    const value = {
      type: 'RDFDatetime',
      value: 0,
    };
    const element = renderTestTemplate(value);
    element.find('input').val('1989-04-20 13:42');
    browserTriggerEvent(element.find('input'), 'change');

    expect(value.value).toBe(609082920000000);
  });

  it('sets current date when "today" button is pressed', () => {
    const value = {
      type: 'RDFDatetime',
      value: 0,
    };
    const baseTime = new Date(Date.UTC(1989, 4, 20));
    jasmine.clock().mockDate(baseTime);

    const element = renderTestTemplate(value);
    browserTriggerEvent(element.find('button[name=Today]'), 'click');

    expect(value.value).toBe(611625600000000);
  });
});


exports = {};
