goog.module('grrUi.stats.comparisonChartDirectiveTest');
goog.setTestOnly();

const {statsModule} = goog.require('grrUi.stats.stats');
const {testsModule} = goog.require('grrUi.tests');


describe('comparison chart directive', () => {
  let $compile;
  let $rootScope;

  beforeEach(module('/static/angular-components/stats/comparison-chart.html'));
  beforeEach(module(statsModule.name));
  beforeEach(module(testsModule.name));

  beforeEach(inject(($injector) => {
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
  }));

  const renderTestTemplate = (typedData, preserveOrder) => {
    $rootScope.typedData = typedData;
    $rootScope.preserveOrder = preserveOrder;

    const template = '<grr-comparison-chart ' +
        'typed-data="typedData" ' +
        'preserve-order="preserveOrder">' +
        '</grr-comparison-chart>';
    const element = $compile(template)($rootScope);
    $rootScope.$apply();

    return element;
  };

  it('shows nothing if the given data is undefined', () => {
    const element = renderTestTemplate();
    expect(element.text()).toContain('No data to display.');

    expect(element.find('th').length).toBe(0);
    expect(element.find('td').length).toBe(0);
  });

  const sampleData = {
    value: {
      data: [
        {value: {label: {value: '< 32768.6s'}, x: {value: 5.55}}},
        {value: {label: {value: '< 16.6s'}, x: {value: 10.55}}},
      ]
    }
  };

  it('shows the given data reverse-sorted if preserveOrder is false', () => {
    const element = renderTestTemplate(sampleData, false);
    // First row corresponds to a greater value: 10.55.
    expect(element.find('tr:nth(1) td:nth(0)').text()).toContain('< 16.6s');
    // Second row corresponds to a smaller value: 5.55.
    expect(element.find('tr:nth(2) td:nth(0)').text()).toContain('< 32768.6s');
  });

  it('shows the given data in the original order if preserveOrder is true', () => {
    const element = renderTestTemplate(sampleData, true);
    expect(element.find('tr:nth(1) td:nth(0)').text()).toContain('< 32768.6s');
    expect(element.find('tr:nth(2) td:nth(0)').text()).toContain('< 16.6s');
  });

  it('updates itself on preserve-order binding changes', () => {
    const element = renderTestTemplate(sampleData, false);
    expect(element.find('tr:nth(1) td:nth(0)').text()).toContain('< 16.6s');

    $rootScope.preserveOrder = true;
    $rootScope.$apply();

    expect(element.find('tr:nth(1) td:nth(0)').text()).toContain('< 32768.6s');
  });
});


exports = {};
