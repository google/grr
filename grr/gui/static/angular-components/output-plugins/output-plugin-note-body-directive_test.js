'use strict';

goog.module('grrUi.outputPlugins.outputPluginNoteBodyDirectiveTest');

const {outputPluginsModule} = goog.require('grrUi.outputPlugins.outputPlugins');
const {testsModule} = goog.require('grrUi.tests');


describe('output plugin note directive', () => {
  let $compile;
  let $rootScope;

  let grrOutputPluginsDirectivesRegistryService;

  beforeEach(module(outputPluginsModule.name));
  beforeEach(module(testsModule.name));

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
    },
  };

  const renderTestTemplate = (outputPlugin) => {
    $rootScope.outputPlugin = outputPlugin || angular.copy(defaultOutputPlugin);

    const template = '<grr-output-plugin-note-body ' +
        'output-plugin="outputPlugin" />';
    const element = $compile(template)($rootScope);
    $rootScope.$apply();

    return element;
  };

  it('shows nothing if no corresponding directive found', () => {
    const element = renderTestTemplate();
    expect(element.text().trim()).toBe('');
  });

  it('renders registered type with a corresponding directive', () => {
    // This directive does not exist and Angular won't process it,
    // but it still will be inserted into DOM and we can check
    // that it's inserted correctly.
    const directiveMock = {
      directive_name: 'theTestDirective',
    };

    grrOutputPluginsDirectivesRegistryService.registerDirective(
        'Foo', directiveMock);

    const element = renderTestTemplate();
    expect($('the-test-directive', element).length).toBe(1);
  });

  it('passes outputPlugin to the corresponding directive', () => {
    const directiveMock = {
      directive_name: 'theTestDirective',
    };

    grrOutputPluginsDirectivesRegistryService.registerDirective(
        'Foo', directiveMock);

    const element = renderTestTemplate();
    const directive = element.find('the-test-directive');
    expect(directive.scope().$eval(directive.attr('output-plugin'))).toEqual(
        defaultOutputPlugin);
  });
});


exports = {};
