goog.module('grrUi.semantic.exactDurationDirectiveTest');
goog.setTestOnly();


const {semanticModule} = goog.require('grrUi.semantic.semantic');
const {testsModule} = goog.require('grrUi.tests');


describe('exact duration directive', () => {
  /*
   * TODO(hanuszczak): Local variables should not contain special characters if
   * not required by the framework. Consider these declarations across all
   * test files.
   */
  let $compile;
  let $rootScope;

  beforeEach(module(semanticModule.name));
  beforeEach(module(testsModule.name));

  beforeEach(inject(($injector) => {
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
  }));

  const renderExactDuration = (value) => {
    $rootScope.value = value;

    const template = '<grr-exact-duration value="value" />';
    const element = $compile(template)($rootScope);
    $rootScope.$apply();

    return element;
  };

  it('shows "-" when value is empty', () => {
    const value = {
      type: 'Duration',
      value: null,
    };

    const element = renderExactDuration(value);
    expect(element.text().trim()).toBe('-');
  });

  it('handles zero-values correctly', () => {
    const value = {
      type: 'Duration',
      value: 0,
    };

    const element = renderExactDuration(value);
    expect(element.text().trim()).toBe('0s');
  });

  it('correctly renders whole seconds', () => {
    const value = {
      type: 'Duration',
      value: 42,
    };

    const element = renderExactDuration(value);
    expect(element.text().trim()).toBe('42s');
  });

  it('correctly renders whole minutes', () => {
    const value = {
      type: 'Duration',
      value: 120,
    };

    const element = renderExactDuration(value);
    expect(element.text().trim()).toBe('2m');
  });

  it('correctly renders whole hours', () => {
    const value = {
      type: 'Duration',
      value: 3600,
    };

    const element = renderExactDuration(value);
    expect(element.text().trim()).toBe('1h');
  });

  it('correctly renders compound values', () => {
    const value = {
      type: 'Duration',
      value: 131 + (new Date('2000-01-20') - new Date('2000-01-01')) / 1000,
    };

    const element = renderExactDuration(value);
    expect(element.text().trim()).toBe('2w 5d 2m 11s');
  });

  it('rounds to nearest seconds', () => {
    const value = {
      type: 'Duration',
      value: 62.5,
    };

    const element = renderExactDuration(value);
    expect(element.text().trim()).toBe('1m 3s');
  });

  it('raises on negative duration values', () => {
    const value = {
      type: 'Duration',
      value: -11,
    };

    expect(() => renderExactDuration(value)).toThrow();
  });
});
