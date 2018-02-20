'use strict';

goog.module('grrUi.core.clientWarningsDirectiveTest');

const {sidebarModule} = goog.require('grrUi.sidebar.sidebar');
const {stubDirective, testsModule} = goog.require('grrUi.tests');


describe('grr-client-warnings directive', () => {
  let $q;
  let $compile;
  let $rootScope;
  let grrApiService;

  beforeEach(module('/static/angular-components/sidebar/client-warnings.html'));
  beforeEach(module(sidebarModule.name));
  beforeEach(module(testsModule.name));

  stubDirective('grrMarkdown');

  beforeEach(inject(($injector) => {
    $q = $injector.get('$q');
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
    grrApiService = $injector.get('grrApiService');
  }));

  const renderTestTemplate = (configOption, client) => {
    $rootScope.client = client || {
      type: 'ApiClient',
      value: {
        labels: [
          {
            type: 'ApiClientLabel',
            value: {
              name: {
                type: 'RDFString',
                value: 'foo'
              }
            }
          },
          {
            type: 'ApiClientLabel',
            value: {
              name: {
                type: 'RDFString',
                value: 'bar'
              }
            }
          }
        ]
      }
    };

    spyOn(grrApiService, 'getV2Cached').and.callFake(() => {
      const deferred = $q.defer();
      const promise = deferred.promise;

      deferred.resolve({
        data: configOption
      });

      return promise;
    });

    const template = '<grr-client-warnings client="client" />';
    const element = $compile(template)($rootScope);
    $rootScope.$apply();

    return element;
  };

  it('does not render anything on empty config option', () => {
    const element = renderTestTemplate({});
    expect(element.find('grr-markdown').length).toBe(0);
  });

  it('does not render anything on empty rules list', () => {
    const element = renderTestTemplate({
      value: {
        rules: []
      }
    });
    expect(element.find('grr-markdown').length).toBe(0);
  });

  it('shows a single warning when one rule matches a single label', () => {
    const element = renderTestTemplate({
      value: {
        rules: [
          {
            withLabels: ['foo'],
            message: 'blah'
          }
        ]
      }
    });
    expect(element.find('grr-markdown').length).toBe(1);

    const markdownElement = element.find('grr-markdown:nth(0)');
    const source = markdownElement.scope().$eval(markdownElement.attr('source'));
    expect(source).toBe('blah');
  });

  it('matches labels in a case-insensitive way', () => {
    const element = renderTestTemplate({
      value: {
        rules: [
          {
            withLabels: ['FOO'],
            message: 'blah'
          }
        ]
      }
    });
    expect(element.find('grr-markdown').length).toBe(1);

    const markdownElement = element.find('grr-markdown:nth(0)');
    const source = markdownElement.scope().$eval(markdownElement.attr('source'));
    expect(source).toBe('blah');
  });

  it('shows a single warning when one rule matches two labels', () => {
    const element = renderTestTemplate({
      value: {
        rules: [
          {
            withLabels: ['foo', 'bar'],
            message: 'blah'
          }
        ]
      }
    });
    expect(element.find('grr-markdown').length).toBe(1);

    const markdownElement = element.find('grr-markdown:nth(0)');
    const source = markdownElement.scope().$eval(markdownElement.attr('source'));
    expect(source).toBe('blah');
  });

  it('shows two warnings when two rules match', () => {
    const element = renderTestTemplate({
      value: {
        rules: [
          {
            withLabels: ['foo'],
            message: 'blah1'
          },
          {
            withLabels: ['bar'],
            message: 'blah2'
          }
        ]
      }
    });
    expect(element.find('grr-markdown').length).toBe(2);

    let markdownElement = element.find('grr-markdown:nth(0)');
    let source = markdownElement.scope().$eval(markdownElement.attr('source'));
    expect(source).toBe('blah1');

    markdownElement = element.find('grr-markdown:nth(1)');
    source = markdownElement.scope().$eval(markdownElement.attr('source'));
    expect(source).toBe('blah2');
  });
});


exports = {};
