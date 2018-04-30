'use strict';

goog.module('grrUi.forms.semanticPrimitiveFormDirectiveTest');

const {browserTriggerEvent, testsModule} = goog.require('grrUi.tests');
const {formsModule} = goog.require('grrUi.forms.forms');


describe('semantic primitive form directive', () => {
  let $compile;
  let $q;
  let $rootScope;
  let grrReflectionService;

  let boolValue;
  let intValue;
  let stringValue;


  beforeEach(module('/static/angular-components/forms/semantic-primitive-form.html'));
  beforeEach(module(formsModule.name));
  beforeEach(module(testsModule.name));

  beforeEach(inject(($injector) => {
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
    $q = $injector.get('$q');
    grrReflectionService = $injector.get('grrReflectionService');

    grrReflectionService.getRDFValueDescriptor = ((valueType) => {
      const deferred = $q.defer();
      deferred.resolve({
        name: valueType,
        mro: [valueType],
      });
      return deferred.promise;
    });

    stringValue = {
      type: 'RDFString',
      value: 'foo',
    };

    intValue = {
      type: 'RDFInteger',
      value: 42,
    };

    boolValue = {
      type: 'RDFBool',
      value: true,
    };
  }));

  const renderTestTemplate = (value) => {
    $rootScope.value = value;

    const template = '<grr-form-primitive value="value" />';
    const element = $compile(template)($rootScope);
    $rootScope.$apply();

    return element;
  };

  it('prefills RDFString value from a model', () => {
    const element = renderTestTemplate(stringValue);
    expect(element.find('input').val()).toBe('foo');
  });

  it('updates RDFString value when model is updated', () => {
    const element = renderTestTemplate(stringValue);
    expect(element.find('input').val()).toBe('foo');

    stringValue.value = 'bar';
    $rootScope.$apply();

    expect(element.find('input').val()).toBe('bar');
  });

  it('updates RDFString model when user changes the input', () => {
    const element = renderTestTemplate(stringValue);

    element.find('input').val('bar');
    browserTriggerEvent(element.find('input'), 'change');
    $rootScope.$apply();

    expect(stringValue.value).toBe('bar');
  });

  it('prefills RDFInteger value from a model', () => {
    const element = renderTestTemplate(intValue);
    expect(element.find('input').val()).toBe('42');
  });

  it('updates RDFInteger value when model is updated', () => {
    const element = renderTestTemplate(intValue);
    expect(element.find('input').val()).toBe('42');

    intValue.value = 84;
    $rootScope.$apply();

    expect(element.find('input').val()).toBe('84');
  });

  it('updates RDFInteger model when user changes the input', () => {
    const element = renderTestTemplate(intValue);

    element.find('input').val('84');
    browserTriggerEvent(element.find('input'), 'change');
    $rootScope.$apply();

    expect(intValue.value).toBe(84);
  });

  it('prefills RDFBool value from a model', () => {
    const element = renderTestTemplate(boolValue);
    expect(element.find('input').prop('checked')).toBe(true);
  });

  it('updates RDFBool value when model is updated', () => {
    const element = renderTestTemplate(boolValue);
    expect(element.find('input').prop('checked')).toBe(true);

    boolValue.value = false;
    $rootScope.$apply();

    expect(element.find('input').prop('checked')).toBe(false);
  });

  it('updates RDFBool model when user changes the input', () => {
    const element = renderTestTemplate(boolValue);

    browserTriggerEvent(element.find('input'), 'click');
    $rootScope.$apply();

    expect(boolValue.value).toBe(false);
  });
});


exports = {};
