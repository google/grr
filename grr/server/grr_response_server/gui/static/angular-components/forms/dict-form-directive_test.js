'use strict';

goog.module('grrUi.forms.dictFormDirectiveTest');

const {browserTriggerEvent, stubDirective, testsModule} = goog.require('grrUi.tests');
const {formsModule} = goog.require('grrUi.forms.forms');


describe('dict form directive', () => {
  let $compile;
  let $q;
  let $rootScope;
  let grrReflectionService;

  beforeEach(module('/static/angular-components/forms/dict-form.html'));
  beforeEach(module(formsModule.name));
  beforeEach(module(testsModule.name));

  stubDirective('grrFormValue');

  beforeEach(inject(($injector) => {
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
    $q = $injector.get('$q');
    grrReflectionService = $injector.get('grrReflectionService');

    grrReflectionService.getRDFValueDescriptor = ((valueType) => {
      if (valueType != 'RDFString') {
        throw new Error('This stub accepts only RDFString value type.');
      }

      const deferred = $q.defer();
      deferred.resolve({
        name: 'RDFString',
        default: {
          type: 'RDFString',
          value: '',
        },
      });
      return deferred.promise;
    });
  }));

  const renderTestTemplate = (value) => {
    $rootScope.value = value;

    const template = '<grr-form-dict value="value" />';
    const element = $compile(template)($rootScope);
    $rootScope.$apply();

    return element;
  };

  const setFormValue = (element, value) => {
    const valueElement = element.find('grr-form-value');
    valueElement.scope().$eval(valueElement.attr('value') + '.value = "' +
        value + '"');
    $rootScope.$apply();
  };

  it('add empty key and value when "+" button is clicked', () => {
    const model = {
      type: 'Dict',
      value: {},
    };
    const element = renderTestTemplate(model);

    browserTriggerEvent(element.find('button[name=Add]'), 'click');

    expect(model).toEqual({
      type: 'Dict',
      value: {'': {type: 'RDFString', value: ''}},
    });
  });

  it('updates the model when key is changed', () => {
    const model = {
      type: 'Dict',
      value: {},
    };
    const element = renderTestTemplate(model);

    browserTriggerEvent(element.find('button[name=Add]'), 'click');

    element.find('input.key').val('foo');
    browserTriggerEvent(element.find('input.key'), 'change');

    expect(model).toEqual({
      type: 'Dict',
      value: {'foo': {type: 'RDFString', value: ''}},
    });
  });

  it('updates the model when value is changed', () => {
    const model = {
      type: 'Dict',
      value: {},
    };
    const element = renderTestTemplate(model);

    browserTriggerEvent(element.find('button[name=Add]'), 'click');
    setFormValue(element, 'foo');

    expect(model).toEqual({
      type: 'Dict',
      value: {'': {type: 'RDFString', value: 'foo'}},
    });
  });

  it('prefills the UI with values from model', () => {
    const model = {
      type: 'Dict',
      value: {'foo': {type: 'RDFString', value: 'bar'}},
    };

    const element = renderTestTemplate(model);
    expect(element.find('input.key').val()).toBe('foo');

    const valueElement = element.find('grr-form-value');
    expect(valueElement.scope().$eval(valueElement.attr('value'))).toEqual(
        {type: 'RDFString', value: 'bar'});
  });

  it('treats digits-only string as integers', () => {
    const model = {
      type: 'Dict',
      value: {},
    };
    const element = renderTestTemplate(model);

    browserTriggerEvent(element.find('button[name=Add]'), 'click');
    setFormValue(element, '42');

    expect(model).toEqual({
      type: 'Dict',
      value: {'': {type: 'RDFInteger', value: 42}},
    });
  });

  it('dynamically changes value type from str to int and back', () => {
    const model = {
      type: 'Dict',
      value: {},
    };
    const element = renderTestTemplate(model);

    browserTriggerEvent(element.find('button[name=Add]'), 'click');

    expect(model).toEqual({
      type: 'Dict',
      value: {'': {type: 'RDFString', value: ''}},
    });

    setFormValue(element, '1');
    expect(model).toEqual({
      type: 'Dict',
      value: {'': {type: 'RDFInteger', value: 1}},
    });

    setFormValue(element, '1a');
    expect(model).toEqual({
      type: 'Dict',
      value: {'': {type: 'RDFString', value: '1a'}},
    });
  });

  it('treats 0x.* strings as hex integers', () => {
    const model = {
      type: 'Dict',
      value: {},
    };
    const element = renderTestTemplate(model);

    browserTriggerEvent(element.find('button[name=Add]'), 'click');
    setFormValue(element, '0x2f');

    expect(model).toEqual({
      type: 'Dict',
      value: {'': {type: 'RDFInteger', value: 47}},
    });
  });

  it('dynamically changes value type from hex int to str and back', () => {
    const model = {
      type: 'Dict',
      value: {},
    };
    const element = renderTestTemplate(model);

    browserTriggerEvent(element.find('button[name=Add]'), 'click');

    expect(model).toEqual({
      type: 'Dict',
      value: {'': {type: 'RDFString', value: ''}},
    });

    setFormValue(element, '0x');
    expect(model).toEqual({
      type: 'Dict',
      value: {'': {type: 'RDFString', value: '0x'}},
    });

    setFormValue(element, '0x2f');
    expect(model).toEqual({
      type: 'Dict',
      value: {'': {type: 'RDFInteger', value: 47}},
    });

    setFormValue(element, '0x2fz');
    expect(model).toEqual({
      type: 'Dict',
      value: {'': {type: 'RDFString', value: '0x2fz'}},
    });
  });

  it('treats "true" string as a boolean', () => {
    const model = {
      type: 'Dict',
      value: {},
    };
    const element = renderTestTemplate(model);

    browserTriggerEvent(element.find('button[name=Add]'), 'click');
    setFormValue(element, 'true');

    expect(model).toEqual({
      type: 'Dict',
      value: {'': {type: 'RDFBool', value: true}},
    });
  });

  it('treats "false" string as a boolean', () => {
    const model = {
      type: 'Dict',
      value: {},
    };
    const element = renderTestTemplate(model);

    browserTriggerEvent(element.find('button[name=Add]'), 'click');
    setFormValue(element, 'false');

    expect(model).toEqual({
      type: 'Dict',
      value: {'': {type: 'RDFBool', value: false}},
    });
  });

  it('dynamically changes valye type from text to bool and back', () => {
    const model = {
      type: 'Dict',
      value: {},
    };
    const element = renderTestTemplate(model);

    browserTriggerEvent(element.find('button[name=Add]'), 'click');

    expect(model).toEqual({
      type: 'Dict',
      value: {'': {type: 'RDFString', value: ''}},
    });

    setFormValue(element, 'true');
    expect(model).toEqual({
      type: 'Dict',
      value: {'': {type: 'RDFBool', value: true}},
    });

    setFormValue(element, 'truea');
    expect(model).toEqual({
      type: 'Dict',
      value: {'': {type: 'RDFString', value: 'truea'}},
    });
  });
});


exports = {};
