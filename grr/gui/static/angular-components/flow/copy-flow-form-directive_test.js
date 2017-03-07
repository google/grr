'use strict';

goog.require('grrUi.flow.module');
goog.require('grrUi.tests.module');
goog.require('grrUi.tests.stubDirective');
goog.require('grrUi.tests.stubTranscludeDirective');

describe('copy flow form directive', function() {
  var $compile, $rootScope, $q, grrApiService;
  var flowObject;

  beforeEach(module('/static/angular-components/flow/copy-flow-form.html'));
  beforeEach(module(grrUi.flow.module.name));
  beforeEach(module(grrUi.tests.module.name));

  grrUi.tests.stubDirective('grrFlowForm');
  grrUi.tests.stubTranscludeDirective('grrConfirmationDialog');

  beforeEach(inject(function($injector) {
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
          }
        },
        runner_args: {
          type: 'FlowRunnerArgs',
          value: {
            rFoo: 'rBar'
          }
        }
      }
    };

    var deferred = $q.defer();
    deferred.resolve({data: flowObject});
    spyOn(grrApiService, 'get').and.returnValue(deferred.promise);
  }));

  var renderTestTemplate = function() {
    $rootScope.clientId = 'C.0000111122223333';
    $rootScope.flowId = 'F:123456';

    var template = '<grr-copy-flow-form ' +
        'client-id="clientId" flow-id="flowId" />';
    var element = $compile(template)($rootScope);
    $rootScope.$apply();

    return element;
  };

  it('fetches existing flow with correct client id and flow id', function() {
    renderTestTemplate();

    expect(grrApiService.get).toHaveBeenCalledWith(
        'clients/C.0000111122223333/flows/F:123456');
  });

  it('sends correct request when grr-confirmation-dialog triggers proceed', function() {
    var element = renderTestTemplate();
    var directive = element.find('grr-confirmation-dialog');

    var deferred = $q.defer();
    spyOn(grrApiService, 'post').and.returnValue(deferred.promise);

    directive.scope().$eval(directive.attr('proceed'));

    expect(grrApiService.post).toHaveBeenCalledWith(
        'clients/C.0000111122223333/flows', {
          flow: {
            args: {
              aFoo: 'aBar'
            },
            runner_args: {
              rFoo: 'rBar',
            }
          }
        });
  });

});
