goog.module('grrUi.semantic.durationDirectiveTest');
goog.setTestOnly();

const {semanticModule} = goog.require('grrUi.semantic.semantic');
const {testsModule} = goog.require('grrUi.tests');


describe('duration directive', () => {
  let $compile;
  let $rootScope;


  beforeEach(module(semanticModule.name));
  beforeEach(module(testsModule.name));

  beforeEach(inject(($injector) => {
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
  }));

  const renderTestTemplate = (value) => {
    $rootScope.value = value;

    const template = '<grr-duration value="value" />';
    const element = $compile(template)($rootScope);
    $rootScope.$apply();

    return element;
  };

  it('gracefully handles cases where passed wrapped object is not defined', () => {
    const element = renderTestTemplate(undefined);
    expect(element.text().trim()).toBe('-');
  });

  it('shows "-" when value is empty', () => {
    const value = {
      type: 'DurationSeconds',
      value: null,
    };
    const element = renderTestTemplate(value);
    expect(element.text().trim()).toBe('-');
  });

  it('shows 0 if duration value is 0', () => {
    const value = {
      type: 'DurationSeconds',
      value: 0,
    };
    const element = renderTestTemplate(value);
    expect(element.text().trim()).toBe('0');
  });

  it('shows duration in seconds if it\'s not divisible by 60', () => {
    const value = {
      type: 'DurationSeconds',
      value: 122,
    };
    const element = renderTestTemplate(value);
    expect(element.text().trim()).toBe('122s');
  });

  it('shows duration in minutes if possible', () => {
    const value = {
      type: 'DurationSeconds',
      value: 120,
    };
    const element = renderTestTemplate(value);
    expect(element.text().trim()).toBe('2m');
  });

  it('shows duration in hours if possible', () => {
    const value = {
      type: 'DurationSeconds',
      value: 7200,
    };
    const element = renderTestTemplate(value);
    expect(element.text().trim()).toBe('2h');
  });

  it('shows duration in days if possible', () => {
    const value = {
      type: 'DurationSeconds',
      value: 172800,
    };
    const element = renderTestTemplate(value);
    expect(element.text().trim()).toBe('2d');
  });

  it('shows duration in weeks if possible', () => {
    const value = {
      type: 'DurationSeconds',
      value: 1209600,
    };
    const element = renderTestTemplate(value);
    expect(element.text().trim()).toBe('2w');
  });

  it('shows duration in days if not divisible by 7', () => {
    const value = {
      type: 'DurationSeconds',
      value: 1036800,
    };
    const element = renderTestTemplate(value);
    expect(element.text().trim()).toBe('12d');
  });
});


exports = {};
