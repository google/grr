'use strict';

goog.module('grrUi.forms.durationFormDirectiveTest');

const {browserTriggerEvent, testsModule} = goog.require('grrUi.tests');
const {formsModule} = goog.require('grrUi.forms.forms');


describe('duration form directive', () => {
  let $compile;
  let $rootScope;


  beforeEach(module('/static/angular-components/forms/duration-form.html'));
  beforeEach(module(formsModule.name));
  beforeEach(module(testsModule.name));

  beforeEach(inject(($injector) => {
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
  }));

  const renderTestTemplate = (value) => {
    $rootScope.value = value;

    const template = '<grr-form-duration value="value" />';
    const element = $compile(template)($rootScope);
    $rootScope.$apply();

    return element;
  };

  it('shows nothing if duration value is null', () => {
    const element = renderTestTemplate({
      type: 'Duration',
      value: null,
    });
    expect(element.find('input').val()).toBe('');
  });

  it('shows 0 if duration value is 0', () => {
    const element = renderTestTemplate({
      type: 'Duration',
      value: 0,
    });
    expect(element.find('input').val()).toBe('0');
  });

  it('shows correct duration for large numbers', () => {
    const element = renderTestTemplate({
      type: 'Duration',
      value: 1040688000000,
    });
    expect(element.find('input').val()).toBe('12045000d');
  });

  it('shows duration in seconds if it\'s not divisible by 60', () => {
    const element = renderTestTemplate({
      type: 'Duration',
      value: 122,
    });
    expect(element.find('input').val()).toBe('122s');
  });

  it('shows duration in minutes if possible', () => {
    const element = renderTestTemplate({
      type: 'Duration',
      value: 120,
    });
    expect(element.find('input').val()).toBe('2m');
  });

  it('shows duration in hours if possible', () => {
    const element = renderTestTemplate({
      type: 'Duration',
      value: 7200,
    });
    expect(element.find('input').val()).toBe('2h');
  });

  it('shows duration in days if possible', () => {
    const element = renderTestTemplate({
      type: 'Duration',
      value: 172800,
    });
    expect(element.find('input').val()).toBe('2d');
  });

  it('shows duration in weeks if possible', () => {
    const element = renderTestTemplate({
      type: 'Duration',
      value: 1209600,
    });
    expect(element.find('input').val()).toBe('2w');
  });

  it('sets value to null on incorrect input', () => {
    const value = {
      type: 'Duration',
      value: 0,
    };
    const element = renderTestTemplate(value);
    element.find('input').val('a');
    browserTriggerEvent(element.find('input'), 'change');

    expect(value.value).toBe(null);
  });

  it('shows warning on incorrect input', () => {
    const value = {
      type: 'Duration',
      value: 0,
    };
    const element = renderTestTemplate(value);
    element.find('input').val('a');
    browserTriggerEvent(element.find('input'), 'change');

    expect(element.text()).toContain('Expected format is');
  });

  it('correctly updates the value when input is in weeks', () => {
    const value = {
      type: 'Duration',
      value: 0,
    };
    const element = renderTestTemplate(value);
    element.find('input').val('2w');
    browserTriggerEvent(element.find('input'), 'change');

    expect(value.value).toBe(1209600);
  });

  it('correctly updates the value when input is in days', () => {
    const value = {
      type: 'Duration',
      value: 0,
    };
    const element = renderTestTemplate(value);
    element.find('input').val('2d');
    browserTriggerEvent(element.find('input'), 'change');

    expect(value.value).toBe(172800);
  });

  it('correctly updates the value when input is in hours', () => {
    const value = {
      type: 'Duration',
      value: 0,
    };
    const element = renderTestTemplate(value);
    element.find('input').val('2h');
    browserTriggerEvent(element.find('input'), 'change');

    expect(value.value).toBe(7200);
  });

  it('correctly updates the value when input is in minutes', () => {
    const value = {
      type: 'Duration',
      value: 0,
    };
    const element = renderTestTemplate(value);
    element.find('input').val('2m');
    browserTriggerEvent(element.find('input'), 'change');

    expect(value.value).toBe(120);
  });

  it('correctly updates the value when input is in seconds', () => {
    const value = {
      type: 'Duration',
      value: 0,
    };
    const element = renderTestTemplate(value);
    element.find('input').val('2s');
    browserTriggerEvent(element.find('input'), 'change');

    expect(value.value).toBe(2);
  });

  it('treats values without unit as seconds', () => {
    const value = {
      type: 'Duration',
      value: 0,
    };
    const element = renderTestTemplate(value);
    element.find('input').val('2');
    browserTriggerEvent(element.find('input'), 'change');

    expect(value.value).toBe(2);
  });
});


exports = {};
