'use strict';

goog.module('grrUi.flow.copyFlowFormDirectiveTest');

const {flowModule} = goog.require('grrUi.flow.flow');
const {stubDirective, stubTranscludeDirective, testsModule} = goog.require('grrUi.tests');


describe('copy flow form directive', () => {
  let $compile;
  let $q;
  let $rootScope;
  let grrApiService;

  let flowObject;

  beforeEach(module('/static/angular-components/flow/copy-flow-form.html'));
  beforeEach(module(flowModule.name));
  beforeEach(module(testsModule.name));

  stubDirective('grrFlowForm');
  stubTranscludeDirective('grrConfirmationDialog');

  beforeEach(inject(($injector) => {
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
    $q = $injector.get('$q');
    grrApiService = $injector.get('grrApiService');

    flowObject = {
      type: 'ApiFlow',
      value: {
        args: {
          type: 'FooFlowArgs',
          value: {
            aFoo: 'aBar',
          },
        },
        runner_args: {
          type: 'FlowRunnerArgs',
          value: {
            rFoo: 'rBar',
          },
        },
      },
    };

    const deferred = $q.defer();
    deferred.resolve({data: flowObject});
    spyOn(grrApiService, 'get').and.returnValue(deferred.promise);
  }));

  const renderTestTemplate = () => {
    $rootScope.clientId = 'C.0000111122223333';
    $rootScope.flowId = 'F:123456';

    const template = '<grr-copy-flow-form ' +
        'client-id="clientId" flow-id="flowId" />';
    const element = $compile(template)($rootScope);
    $rootScope.$apply();

    return element;
  };

  it('fetches existing flow with correct client id and flow id', () => {
    renderTestTemplate();

    expect(grrApiService.get).toHaveBeenCalledWith(
        'clients/C.0000111122223333/flows/F:123456');
  });

  it('sends correct request when grr-confirmation-dialog triggers proceed',
     () => {
       const element = renderTestTemplate();
       const directive = element.find('grr-confirmation-dialog');

       const deferred = $q.defer();
       spyOn(grrApiService, 'post').and.returnValue(deferred.promise);

       directive.scope().$eval(directive.attr('proceed'));

       expect(grrApiService.post)
           .toHaveBeenCalledWith('clients/C.0000111122223333/flows', {
             flow: {
               args: {
                 aFoo: 'aBar',
               },
               runner_args: {
                 rFoo: 'rBar',
               },
             },
             original_flow: {
               flow_id: 'F:123456',
               client_id: 'C.0000111122223333',
             },
           });
     });
});


exports = {};
