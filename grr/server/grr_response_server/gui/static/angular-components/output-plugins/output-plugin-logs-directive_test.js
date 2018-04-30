'use strict';

goog.module('grrUi.outputPlugins.outputPluginLogsDirectiveTest');

const {browserTriggerEvent, stubDirective, testsModule} = goog.require('grrUi.tests');
const {outputPluginsModule} = goog.require('grrUi.outputPlugins.outputPlugins');


describe('output plugin logs directive', () => {
  let $compile;
  let $q;
  let $rootScope;
  let $timeout;
  let grrApiService;


  beforeEach(module('/static/angular-components/output-plugins/output-plugin-logs.html'));
  beforeEach(module('/static/angular-components/output-plugins/output-plugin-logs-modal.html'));
  beforeEach(module(outputPluginsModule.name));
  beforeEach(module(testsModule.name));

  stubDirective('grrPagedFilteredTable');

  beforeEach(inject(($injector) => {
    $q = $injector.get('$q');
    $compile = $injector.get('$compile');
    $timeout = $injector.get('$timeout');
    $rootScope = $injector.get('$rootScope');
    grrApiService = $injector.get('grrApiService');
  }));

  const renderTestTemplate = () => {
    $rootScope.url = 'foo/bar';

    const template = '<grr-output-plugin-logs url="url" label="a foo"' +
        'css-class="label-danger" icon="foo-icon" />';
    const element = $compile(template)($rootScope);
    $rootScope.$apply();

    return element;
  };

  it('fetches and show items count', () => {
    const deferred = $q.defer();
    deferred.resolve({
      data: {
        total_count: 42,
      },
    });
    spyOn(grrApiService, 'get').and.returnValue(deferred.promise);

    const element = renderTestTemplate();

    expect(element.text()).toContain('42');
  });

  it('shows nothing if total_count is 0', () => {
    const deferred = $q.defer();
    deferred.resolve({
      data: {
        total_count: 0,
      },
    });
    spyOn(grrApiService, 'get').and.returnValue(deferred.promise);

    const element = renderTestTemplate();

    expect(element.text().trim()).toBe('');
  });


  describe('inspect dialog', () => {
    beforeEach(() => {
      const deferred = $q.defer();
      deferred.resolve({
        data: {
          total_count: 42,
        },
      });
      spyOn(grrApiService, 'get').and.returnValue(deferred.promise);
    });

    afterEach(() => {
      // We have to clean document's body to remove modal windows that were not
      // closed.
      $(document.body).html('');
    });

    it('is shown when label is clicked', () => {
      const element = renderTestTemplate();
      browserTriggerEvent(element.find('.label'), 'click');

      expect($(document.body).text()).toContain(
          'Inspect a foo');
    });

    it('closes when close button is clicked', () => {
      const element = renderTestTemplate();
      browserTriggerEvent(element.find('.label'), 'click');

      browserTriggerEvent($('button.close'), 'click');
      $timeout.flush();
      expect($(document.body).text()).not.toContain(
          'Inspect a foo');
    });
  });
});


exports = {};
