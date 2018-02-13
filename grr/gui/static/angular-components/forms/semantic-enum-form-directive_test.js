'use strict';

goog.module('grrUi.forms.semanticEnumFormDirectiveTest');

const {browserTriggerEvent, testsModule} = goog.require('grrUi.tests');
const {formsModule} = goog.require('grrUi.forms.forms');


describe('semantic enum form directive', () => {
  let $compile;
  let $rootScope;
  let value;


  beforeEach(module('/static/angular-components/forms/semantic-enum-form.html'));
  beforeEach(module(formsModule.name));
  beforeEach(module(testsModule.name));

  beforeEach(inject(($injector) => {
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');

    value = {
      age: 0,
      type: 'EnumNamedValue',
      value: 'NONE',
      mro: [
        'EnumNamedValue', 'RDFInteger', 'RDFString', 'RDFBytes', 'RDFValue',
        'object'
      ],
    };
  }));

  const renderTestTemplate = (metadata) => {
    $rootScope.value = value;
    $rootScope.metadata = metadata;

    const template = '<grr-form-enum metadata="metadata" value="value" />';
    const element = $compile(template)($rootScope);
    $rootScope.$apply();

    return element;
  };

  it('shows list of options from the metadata', () => {
    const element = renderTestTemplate({
      allowed_values: [
        {name: 'NONE', value: 0},
        {name: 'CHOICE 1', value: 1},
        {name: 'CHOICE 2', value: 2},
      ],
    });

    expect(element.find('option').length).toBe(3);
    expect(element.find('option:nth(0)').attr('label')).toBe('NONE');
    expect(element.find('option:nth(1)').attr('label')).toBe('CHOICE 1');
    expect(element.find('option:nth(2)').attr('label')).toBe('CHOICE 2');
  });

  it('marks the default value with "(default)"', () => {
    const element = renderTestTemplate({
      allowed_values: [
        {name: 'NONE', value: 0},
        {name: 'CHOICE 1', value: 1},
        {name: 'CHOICE 2', value: 2},
      ],
      default: {
        'age': 0,
        'type': 'EnumNamedValue',
        'value': 'CHOICE 1',
        'mro': [
          'EnumNamedValue', 'RDFInteger', 'RDFString', 'RDFBytes', 'RDFValue',
          'object'
        ]
      },
    });

    expect(element.find('option').length).toBe(3);
    expect(element.find('option:nth(0)').attr('label')).toBe('NONE');
    expect(element.find('option:nth(1)').attr('label')).toBe(
        'CHOICE 1 (default)');
    expect(element.find('option:nth(2)').attr('label')).toBe('CHOICE 2');
  });

  it('updates the value when user selects an option', () => {
    const element = renderTestTemplate({
      allowed_values: [
        {name: 'NONE', value: 0},
        {name: 'CHOICE 1', value: 1},
        {name: 'CHOICE 2', value: 2},
      ],
    });

    expect(value.value).toBe('NONE');

    element.find('select').val(
        element.find('select option[label="CHOICE 2"]').val());
    browserTriggerEvent(element.find('select'), 'change');
    $rootScope.$apply();

    expect(value.value).toBe('CHOICE 2');
  });
});


exports = {};
