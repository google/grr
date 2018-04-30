'use strict';

goog.module('grrUi.forms.outputPluginDescriptorFormDirectiveTest');

const {browserTriggerEvent, stubDirective, testsModule} = goog.require('grrUi.tests');
const {formsModule} = goog.require('grrUi.forms.forms');


describe('grr-output-plugin-descriptor-form directive', () => {
  let $compile;
  let $q;
  let $rootScope;
  let grrApiService;
  let grrReflectionService;


  beforeEach(module('/static/angular-components/forms/' +
      'output-plugin-descriptor-form.html'));
  beforeEach(module(formsModule.name));
  beforeEach(module(testsModule.name));

  // Stub out grr-form-value directive, as arguments rendering is going
  // to be delegated to it.
  stubDirective('grrFormValue');

  beforeEach(inject(($injector) => {
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
    $q = $injector.get('$q');
    grrApiService = $injector.get('grrApiService');
    grrReflectionService = $injector.get('grrReflectionService');

    const apiServiceResponse = $q.defer();
    apiServiceResponse.resolve({
      data: {
        items: [
          {
            args_type: 'FooOutputPluginArgs',
            name: 'FooOutputPlugin',
            plugin_type: 'LEGACY',
          },
          {
            args_type: 'BarOutputPluginArgs',
            name: 'BarOutputPlugin',
            plugin_type: 'LEGACY',
          },
          {
            name: 'foo-bar',
            friendly_name: 'FooBar plugin',
            plugin_type: 'INSTANT',
          },
        ],
      },
    });
    spyOn(grrApiService, 'get').and.returnValue(apiServiceResponse.promise);

    spyOn(grrReflectionService, 'getRDFValueDescriptor')
        .and.callFake((name) => {
          const deferred = $q.defer();

          if (name == 'FooOutputPluginArgs') {
            deferred.resolve({
              default: {
                type: 'FooOutputPluginArgs',
                value: 'FooValue',
              },
            });
          } else if (name == 'BarOutputPluginArgs') {
            deferred.resolve({
              default: {
                type: 'BarOutputPluginArgs',
                value: 'BarValue',
              },
            });
          } else {
            throw new Error(`Unexpected name: ${name}`);
          }

          return deferred.promise;
        });
  }));

  const renderTestTemplate = (value) => {
    $rootScope.value = angular.isDefined(value) ? value : {
      type: 'OutputPluginDescriptor',
      value: {},
    };

    const template = '<grr-output-plugin-descriptor-form value="value" />';
    const element = $compile(template)($rootScope);
    $rootScope.$apply();

    return element;
  };

  it('selects alphabetically first plugin if none is specified', () => {
    const element = renderTestTemplate();

    expect($rootScope.value.value.plugin_name.value).toBe('BarOutputPlugin');
    expect(element.find('select').val()).toBe('string:BarOutputPlugin');
  });

  it('keeps current output plugin type if one is specified', () => {
    const element = renderTestTemplate({
      type: 'OutputPluginDescriptor',
      value: {
        plugin_name: {
          type: 'RDFString',
          value: 'FooOutputPlugin',
        },
      },
    });

    expect($rootScope.value.value.plugin_name.value).toBe('FooOutputPlugin');
    expect(element.find('select').val()).toBe('string:FooOutputPlugin');
  });

  it('sets plugin args to default when plugin type is changed', () => {
    const element = renderTestTemplate();

    expect($rootScope.value.value.plugin_args.type).toBe('BarOutputPluginArgs');

    element.find('select').val(
        element.find('select option[label="FooOutputPlugin"]').val());
    browserTriggerEvent(element.find('select'), 'change');
    expect($rootScope.value.value.plugin_args.type).toBe('FooOutputPluginArgs');
  });

  it('delegates current plugin args rendering to grr-form-value', () => {
    const element = renderTestTemplate();

    let argsValue =
        $rootScope.$eval(element.find('grr-form-value').attr('value'));
    expect(argsValue.type).toBe('BarOutputPluginArgs');

    element.find('select').val(
        element.find('select option[label="FooOutputPlugin"]').val());
    browserTriggerEvent(element.find('select'), 'change');

    argsValue = $rootScope.$eval(element.find('grr-form-value').attr('value'));
    expect(argsValue.type).toBe('FooOutputPluginArgs');
  });
});


exports = {};
