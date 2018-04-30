'use strict';

goog.module('grrUi.semantic.byteSizeDirectiveTest');

const {semanticModule} = goog.require('grrUi.semantic.semantic');
const {testsModule} = goog.require('grrUi.tests');


describe('grrByteSize directive', () => {
  let $compile;
  let $rootScope;


  beforeEach(module('/static/angular-components/semantic/byte-size.html'));
  beforeEach(module(semanticModule.name));
  beforeEach(module(testsModule.name));

  beforeEach(inject(($injector) => {
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
  }));

  const renderTestTemplate = (value) => {
    $rootScope.value = value;

    const template = '<grr-byte-size value="value" />';
    const element = $compile(template)($rootScope);
    $rootScope.$apply();

    return element;
  };

  it('shows "-" when value is empty', () => {
    const value = {
      type: 'ByteSize',
      value: null,
    };
    const element = renderTestTemplate(value);
    expect(element.text().trim()).toBe('-');
  });

  it('shows 0 if value is 0', () => {
    const value = {
      type: 'ByteSize',
      value: 0,
    };
    const element = renderTestTemplate(value);
    expect(element.text().trim()).toBe('0');
  });

  it('shows value in bytes if it is less than 1024', () => {
    const value = {
      type: 'ByteSize',
      value: 42,
    };
    const element = renderTestTemplate(value);
    expect(element.text().trim()).toBe('42B');
  });

  it('shows value in kibibytes if it is less than 1024**2', () => {
    const value = {
      type: 'ByteSize',
      value: 1124,
    };
    const element = renderTestTemplate(value);
    expect(element.text().trim()).toBe('1.1KiB');
  });

  it('shows value in mebibytes if it is less than 1024**3', () => {
    const value = {
      type: 'ByteSize',
      value: 44040192,
    };
    const element = renderTestTemplate(value);
    expect(element.text().trim()).toBe('42MiB');
  });

  it('shows value in gibibytes if it is more than 1024**3', () => {
    const value = {
      type: 'ByteSize',
      value: 1610612736,
    };
    const element = renderTestTemplate(value);
    expect(element.text().trim()).toBe('1.5GiB');
  });

  it('shows value in bytes in the tooltip', () => {
    const value = {
      type: 'ByteSize',
      value: 1610612736,
    };
    const element = renderTestTemplate(value);
    expect(element.find('span').attr('title')).toBe('1610612736 bytes');
  });
});


exports = {};
