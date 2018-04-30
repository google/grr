'use strict';

goog.module('grrUi.flow.flowFormDirectiveTest');

const {flowModule} = goog.require('grrUi.flow.flow');
const {stubDirective, testsModule} = goog.require('grrUi.tests');


describe('flow form directive', () => {
  let $compile;
  let $q;
  let $rootScope;
  let grrReflectionService;


  beforeEach(module('/static/angular-components/flow/flow-form.html'));
  beforeEach(module(flowModule.name));
  beforeEach(module(testsModule.name));

  // Stub out grr-form-value and grr-form-proto-repeated-field directives,
  // as all rendering is going to be delegated to them.
  angular.forEach(
      ['grrFormValue', 'grrFormProtoRepeatedField'], (directiveName) => {
        stubDirective(directiveName);
      });

  beforeEach(inject(($injector) => {
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
    $q = $injector.get('$q');
    grrReflectionService = $injector.get('grrReflectionService');

    spyOn(grrReflectionService, 'getRDFValueDescriptor')
        .and.callFake((valueType) => {
          const deferred = $q.defer();

          if (valueType == 'FlowRunnerArgs') {
            deferred.resolve({
              default: {
                type: 'FlowRunnerArgs',
                value: {},
              },
              fields: [
                {
                  name: 'output_plugins',
                  default: [],
                  foo: 'bar',
                },
              ],
            });
          } else if (valueType == 'OutputPluginDescriptor') {
            deferred.resolve({
              default: {
                type: 'OutputPluginDescriptor',
                value: 'OutputPluginDescriptor-default',
                foo: 'bar',
              },
            });
          }

          return deferred.promise;
        });
  }));

  const renderTestTemplate = (args, runnerArgs, withOutputPlugins) => {
    $rootScope.clientId = 'C.0000111122223333';
    $rootScope.args = args || {
      type: 'FooFlowArgs',
      value: {
        foo: 'bar',
      },
    };

    $rootScope.runnerArgs = runnerArgs || {
      type: 'FlowRunnerArgs',
      value: {
        flow_name: {
          type: 'RDFString',
          value: 'FooFlow',
        },
      },
    };

    if (angular.isUndefined(withOutputPlugins)) {
      withOutputPlugins = true;
    }
    $rootScope.withOutputPlugins = withOutputPlugins;

    const template = '<grr-flow-form ' +
        'flow-args="args" flow-runner-args="runnerArgs" ' +
        'with-output-plugins="withOutputPlugins" ' +
        'has-errors="hasErrors" />';
    const element = $compile(template)($rootScope);
    $rootScope.$apply();

    return element;
  };

  it('shows flow arguments form', () => {
    const element = renderTestTemplate();
    const directive = element.find('grr-form-value:nth(0)');

    expect(directive.scope().$eval(directive.attr('value'))).toEqual(
        $rootScope.args);
  });

  it('shows flow runner arguments form', () => {
    const element = renderTestTemplate();
    const directive = element.find('grr-form-value:nth(1)');

    // This should be equal to flow runner arguments default + initialized
    // empty output plugins list.
    const expected = angular.copy($rootScope.runnerArgs);
    expected['value']['output_plugins'] = [];
    expect(directive.scope().$eval(directive.attr('value'))).toEqual(expected);
  });

  it('preserves existing output plugins list', () => {
    const runnerArgs = {
      type: 'FlowRunnerArgs',
      value: {
        flow_name: {
          type: 'RDFString',
          value: 'FooFlow',
        },
        output_plugins: [
          {
            type: 'FooPluginArgs',
            value: {},
          },
        ],
      },
    };
    const element = renderTestTemplate(undefined, angular.copy(runnerArgs));
    const directive = element.find('grr-form-value:nth(1)');
    expect(directive.scope().$eval(directive.attr('value'))).toEqual(runnerArgs);
  });

  it('does not show output plugins if with-output-plugns=false', () => {
    const element = renderTestTemplate(undefined, undefined, false);
    const directive = element.find('grr-form-value:nth(1)');

    // This should be equal to flow runner arguments default. output_plugins
    // list is not initialized as no output plugins form controls are present.
    expect(directive.scope().$eval(directive.attr('value'))).toEqual(
        angular.copy($rootScope.runnerArgs));

    const pluginsDirective = element.find('grr-form-proto-repeated-field');
    expect(pluginsDirective.length).toBe(0);
  });

  it('shows output plugins list form', () => {
    const element = renderTestTemplate();
    const directive = element.find('grr-form-proto-repeated-field');

    // This should be equal to output plugin descriptor.
    expect(directive.scope().$eval(directive.attr('descriptor'))).toEqual({
      default: {
        type: 'OutputPluginDescriptor',
        value: 'OutputPluginDescriptor-default',
        foo: 'bar',
      },
    });

    // This should be equal to output plugins field from flor runner arguments
    // descriptor.
    expect(directive.scope().$eval(directive.attr('field'))).toEqual({
      name: 'output_plugins',
      default: [],
      foo: 'bar',
    });

    // Output plugins list is empty by default.
    expect(directive.scope().$eval(directive.attr('value'))).toEqual([]);
  });

  it('updates has-errors binding if flow arguments are invalid', () => {
    renderTestTemplate();

    expect($rootScope.hasErrors).toBe(false);

    $rootScope.args['validationError'] = 'Oh no!';
    $rootScope.$apply();

    expect($rootScope.hasErrors).toBe(true);
  });

  it('updates has-errors binding if runner arguments are invalid', () => {
    renderTestTemplate();

    expect($rootScope.hasErrors).toBe(false);

    $rootScope.runnerArgs['validationError'] = 'Oh no!';
    $rootScope.$apply();

    expect($rootScope.hasErrors).toBe(true);
  });
});


exports = {};
