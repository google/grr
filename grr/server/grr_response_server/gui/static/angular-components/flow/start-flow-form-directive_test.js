'use strict';

goog.module('grrUi.flow.startFlowFormDirectiveTest');

const {browserTriggerEvent, stubDirective, testsModule} = goog.require('grrUi.tests');
const {flowModule} = goog.require('grrUi.flow.flow');


describe('start flow form directive', () => {
  let $compile;
  let $q;
  let $rootScope;
  let grrApiService;
  let grrReflectionService;

  let flowRunnerArgsDefault;

  beforeEach(module('/static/angular-components/flow/start-flow-form.html'));
  beforeEach(module(flowModule.name));
  beforeEach(module(testsModule.name));

  // Stub out grr-semantic-value and grr-flow-form directives, as all
  // rendering is going to be delegated to them.
  angular.forEach(['grrFlowForm', 'grrSemanticValue'], (directiveName) => {
    stubDirective(directiveName);
  });

  beforeEach(inject(($injector) => {
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
    $q = $injector.get('$q');
    grrApiService = $injector.get('grrApiService');
    grrReflectionService = $injector.get('grrReflectionService');

    flowRunnerArgsDefault = {
      type: 'FlowRunnerArgs',
      value: {
        flow_name: {
          type: 'RDFString',
          value: 'FooFlow',
        },
        output_plugins: [
          {
            foo: 'bar',
          },
        ],
        foo: 'bar',
      },
    };

    const deferred = $q.defer();
    deferred.resolve({
      default: flowRunnerArgsDefault,
    });
    spyOn(grrReflectionService, 'getRDFValueDescriptor').and.returnValue(
        deferred.promise);
  }));

  const renderTestTemplate = () => {
    $rootScope.clientId = 'C.0000111122223333';
    $rootScope.descriptor = {
      type: 'ApiFlowDescriptor',
      value: {
        name: {
          type: 'RDFString',
          value: 'FooFlow',
        },
        default_args: {
          type: 'FooFlowArgs',
          value: {
            foo: 'bar',
          },
        },
      },
    };

    const template = '<grr-start-flow-form ' +
        'client-id="clientId" descriptor="descriptor" />';
    const element = $compile(template)($rootScope);
    $rootScope.$apply();

    return element;
  };

  it('shows flow arguments form', () => {
    const element = renderTestTemplate();
    const directive = element.find('grr-flow-form');

    expect(directive.scope().$eval(directive.attr('flow-args'))).toEqual(
        $rootScope.descriptor['value']['default_args']);
    expect(directive.scope().$eval(directive.attr('flow-runner-args'))).toEqual(
        flowRunnerArgsDefault);
  });

  it('sends request when Launch button is clicked', () => {
    const element = renderTestTemplate();

    const deferred = $q.defer();
    spyOn(grrApiService, 'post').and.returnValue(deferred.promise);

    browserTriggerEvent(element.find('button.Launch'), 'click');

    expect(grrApiService.post)
        .toHaveBeenCalledWith('/clients/C.0000111122223333/flows', {
          flow: {
            runner_args: {
              flow_name: 'FooFlow',
              output_plugins: [{foo: 'bar'}],
              foo: 'bar',
            },
            args: {
              foo: 'bar',
            },
          },
        });
  });

  it('respects changes in form data when sending request', () => {
    const element = renderTestTemplate();

    const directive = element.find('grr-flow-form:nth(0)');
    // Change flow args.
    directive.scope().$eval(directive.attr('flow-args'))['value']['changed'] = true;
    // Change flow runner args.
    directive.scope().$eval(directive.attr('flow-runner-args'))['value']['changed'] = true;
    // Change output plugins value.
    directive.scope().$eval(directive.attr('flow-runner-args'))['value']['output_plugins'].push(42);

    // Apply the changes.
    $rootScope.$apply();

    // Now click the Launch button.
    const deferred = $q.defer();
    spyOn(grrApiService, 'post').and.returnValue(deferred.promise);
    browserTriggerEvent(element.find('button.Launch'), 'click');

    expect(grrApiService.post)
        .toHaveBeenCalledWith('/clients/C.0000111122223333/flows', {
          flow: {
            runner_args: {
              flow_name: 'FooFlow',
              output_plugins: [{foo: 'bar'}, 42],
              changed: true,
              foo: 'bar',
            },
            args: {
              foo: 'bar',
              changed: true,
            },
          },
        });
  });

  it('shows progress message when request is processed', () => {
    const element = renderTestTemplate();

    const deferred = $q.defer();
    spyOn(grrApiService, 'post').and.returnValue(deferred.promise);

    browserTriggerEvent(element.find('button.Launch'), 'click');

    expect(element.text()).toContain('Launching flow FooFlow...');
  });

  it('shows flow summary when launch succeeds', () => {
    const element = renderTestTemplate();

    const deferred = $q.defer();
    spyOn(grrApiService, 'post').and.returnValue(deferred.promise);

    browserTriggerEvent(element.find('button.Launch'), 'click');

    const flow = {
      args: {'foo1': 'bar1'},
      runner_args: {'foo2': 'bar2'},
    };
    deferred.resolve({
      data: flow,
    });
    $rootScope.$apply();

    const directive = element.find('grr-semantic-value:nth(0)');
    expect(directive.scope().$eval(directive.attr('value'))).toEqual(flow);
  });

  it('shows failure message when launch fails', () => {
    const element = renderTestTemplate();

    const deferred = $q.defer();
    spyOn(grrApiService, 'post').and.returnValue(deferred.promise);

    browserTriggerEvent(element.find('button.Launch'), 'click');

    deferred.reject({
      data: {
        message: 'Something is wrong',
      },
    });
    $rootScope.$apply();

    expect(element.text()).toContain('Something is wrong');
  });
});


exports = {};
