'use strict';

goog.module('grrUi.outputPlugins.outputPluginNoteDirectiveTest');

const {outputPluginsModule} = goog.require('grrUi.outputPlugins.outputPlugins');
const {stubDirective, testsModule} = goog.require('grrUi.tests');


describe('output plugin note directive', () => {
  let $compile;
  let $rootScope;

  let grrOutputPluginsDirectivesRegistryService;

  beforeEach(module('/static/angular-components/output-plugins/output-plugin-note.html'));
  beforeEach(module(outputPluginsModule.name));
  beforeEach(module(testsModule.name));

  stubDirective('grrOutputPluginNoteBody');
  stubDirective('grrOutputPluginLogs');

  beforeEach(inject(($injector) => {
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');

    grrOutputPluginsDirectivesRegistryService = $injector.get(
        'grrOutputPluginsDirectivesRegistryService');
  }));

  const defaultOutputPlugin = {
    value: {
      plugin_descriptor: {
        value: {
          plugin_name: {
            value: 'Foo',
          },
        },
      },
      id: {
        value: '42',
      },
    },
  };

  const renderTestTemplate = (outputPlugin) => {
    $rootScope.outputPlugin = outputPlugin || angular.copy(defaultOutputPlugin);
    $rootScope.outputPluginsUrl = '/foo/bar';

    const template = '<grr-output-plugin-note output-plugin="outputPlugin" ' +
        'output-plugins-url="outputPluginsUrl" />';
    const element = $compile(template)($rootScope);
    $rootScope.$apply();

    return element;
  };

  it('shows registered plugin title if registered', () => {
    let element = renderTestTemplate();
    expect(element.text()).toContain('');

    const directiveMock = {
      directive_name: 'theTestDirective',
      output_plugin_title: 'a bar plugin',
    };
    grrOutputPluginsDirectivesRegistryService.registerDirective(
        'Foo', directiveMock);

    element = renderTestTemplate();
    expect(element.text()).toContain('a bar plugin');
  });

  it('shows plugin descriptor name if not registered', () => {
    const element = renderTestTemplate();
    expect(element.text()).toContain('Foo');
  });

  it('delegates rendering to grr-output-plugin-note-body', () => {
    const element = renderTestTemplate();

    const body = element.find('grr-output-plugin-note-body');
    expect(body.scope().$eval(body.attr('output-plugin'))).toEqual(
        defaultOutputPlugin);
  });

  it('delegates logs info rendering to grr-output-plugin-logs', () => {
    const element = renderTestTemplate();

    const logs = element.find('grr-output-plugin-logs:nth(0)');
    expect(logs.scope().$eval(logs.attr('url'))).toEqual(
        '/foo/bar/42/logs');
  });

  it('delegates errors info rendering to grr-output-plugin-logs', () => {
    const element = renderTestTemplate();

    const errors = element.find('grr-output-plugin-logs:nth(1)');
    expect(errors.scope().$eval(errors.attr('url'))).toEqual(
        '/foo/bar/42/errors');
  });
});


exports = {};
