'use strict';

goog.module('grrUi.forms.semanticProtoSingleFieldFormDirectiveTest');

const {formsModule} = goog.require('grrUi.forms.forms');
const {testsModule} = goog.require('grrUi.tests');


describe('semantic proto single field form directive', () => {
  let $compile;
  let $rootScope;


  beforeEach(module('/static/angular-components/forms/semantic-proto-form.html'));
  beforeEach(module('/static/angular-components/forms/semantic-proto-union-form.html'));
  beforeEach(module('/static/angular-components/forms/semantic-proto-single-field-form.html'));
  beforeEach(module('/static/angular-components/forms/semantic-proto-repeated-field-form.html'));
  beforeEach(module(formsModule.name));
  beforeEach(module(testsModule.name));

  beforeEach(inject(($injector) => {
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
  }));

  const renderTestTemplate = (value, field) => {
    $rootScope.value = value;
    $rootScope.field = field;

    const template = '<grr-form-proto-single-field value="value" ' +
        'field="field" />';
    const element = $compile(template)($rootScope);
    $rootScope.$apply();

    return element;
  };

  it('renders doc and friendly name', () => {
    const element = renderTestTemplate({}, {
      doc: 'Field documentation',
      friendly_name: 'Field friendly name',
    });

    expect(element.find('label[title="Field documentation"]').length).toBe(1);
    expect(element.text()).toContain('Field friendly name');
  });

  it('delegates rendering to grr-form-value', () => {
    const element = renderTestTemplate({}, {});

    expect(element.find('grr-form-value').length).toBe(1);
  });
});


exports = {};
