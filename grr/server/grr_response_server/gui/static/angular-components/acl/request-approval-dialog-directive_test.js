goog.module('grrUi.acl.requestApprovalDialogDirectiveTest');
goog.setTestOnly();

const {aclModule} = goog.require('grrUi.acl.acl');
const {browserTriggerEvent, testsModule, stubDirective} = goog.require('grrUi.tests');

describe('request approval dialog', () => {
  let $compile;
  let $q;
  let $rootScope;
  let closeSpy;
  let dismissSpy;
  let grrApiService;

  beforeEach(module('/static/angular-components/acl/' +
      'request-approval-dialog.html'));
  beforeEach(module('/static/angular-components/core/' +
      'confirmation-dialog.html'));

  beforeEach(module(aclModule.name));
  beforeEach(module(testsModule.name));

  stubDirective('grrApproverInput');

  beforeEach(inject(($injector) => {
    $q = $injector.get('$q');
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
    grrApiService = $injector.get('grrApiService');

    closeSpy = jasmine.createSpy('close');
    dismissSpy = jasmine.createSpy('dismiss');
  }));

  const renderTestTemplate =
      ((approvalType, createUrl, createArgs, description, reason) => {
        $rootScope.approvalType = approvalType;
        $rootScope.createUrl = createUrl;
        $rootScope.createArgs = createArgs;
        $rootScope.description = description;
        $rootScope.reason = reason;

        $rootScope.$close = closeSpy;
        $rootScope.$dismiss = dismissSpy;

        const template = '<grr-request-approval-dialog ' +
            'approval-type="approvalType" ' +
            'create-request-url="createUrl" ' +
            'create-request-args="createArgs" ' +
            'access-error-description="description" ' +
            'reason="reason" />';

        const element = $compile(template)($rootScope);
        $rootScope.$apply();

        return element;
      });

  const setApproverInput = (element, value) => {
    const valueElement = element.find('grr-approver-input');
    const valueAttr = valueElement.attr('ng-model');
    const expression = `${valueAttr} = "${value}"`;
    valueElement.scope().$eval(expression);
  };

  let approvals;
  let clientApprovalRequest;
  let configEntry;

  beforeEach(() => {
    clientApprovalRequest = {
      client_id: 'C:123456',
      approval: {},
    };

    approvals = {
      data: {
        items: [
          {
            type: 'ApiClientApproval',
            value: {
              reason: {
                type: 'RDFString',
                value: 'reason1',
              },
            },
          },
          {
            type: 'ApiClientApproval',
            value: {
              reason: {
                type: 'RDFString',
                value: 'reason2',
              },
            },
          },
        ],
      },
    };

    configEntry = {
      data: {
        value: {
          type: 'RDFString',
          value: 'foo@bar.com, xyz@example.com',
        },
      },
    };

    let deferred = $q.defer();
    deferred.resolve(configEntry);
    spyOn(grrApiService, 'getCached').and.returnValue(deferred.promise);

    deferred = $q.defer();
    deferred.resolve(approvals);
    spyOn(grrApiService, 'get').and.returnValue(deferred.promise);
  });

  it('shows a list of previous client reasons', () => {
    const element = renderTestTemplate('client');

    expect($('select option', element).length).toBe(3);
    expect($('select option:nth(0)', element).val()).toEqual('');
    expect($('select option:nth(1)', element).val()).toEqual('reason1');
    expect($('select option:nth(2)', element).val()).toEqual('reason2');
  });

  it('doesn\'t show a list of CC addresses when not available', () => {
    configEntry['data']['value']['value'] = undefined;
    const element = renderTestTemplate('client');

    expect(element.text()).not.toContain('CC');
    expect($('input[name=cc_approval]', element).length).toBe(0);
  });

  it('shows a list of CC addresses when they\'re available', () => {
    const element = renderTestTemplate('client');

    expect(element.text()).toContain('CC foo@bar.com, xyz@example.com');
    expect($('input[name=cc_approval]', element).length).toBe(1);
  });

  it('disables reason field when dropdown reason is selected', () => {
    const element = renderTestTemplate('client');

    $('select', element).val('reason1');
    browserTriggerEvent($('select', element), 'change');

    expect($('input[name=acl_reason]', element).attr('disabled')).toBeTruthy();
  });

  it('includes approvers into request if CC-checbox is selected', () => {
    spyOn(grrApiService, 'post').and.returnValue($q.defer().promise);

    const element =
        renderTestTemplate('client', 'foo/bar', clientApprovalRequest);

    setApproverInput(element, 'foo');

    $('input[name=acl_reason]', element).val('bar');
    browserTriggerEvent($('input[name=acl_reason]', element), 'change');

    $('input[name=cc_approval]', element).prop('checked', true);
    browserTriggerEvent($('input[name=cc_approval]', element), 'change');

    browserTriggerEvent($('button[name=Proceed]', element), 'click');

    expect(grrApiService.post).toHaveBeenCalledWith('foo/bar', {
      client_id: 'C:123456',
      approval: {
        reason: 'bar',
        notified_users: ['foo'],
        email_cc_addresses: ['foo@bar.com', 'xyz@example.com'],
      },
    });
  });

  it('includes dropdown reason into request', () => {
    spyOn(grrApiService, 'post').and.returnValue($q.defer().promise);

    const element =
        renderTestTemplate('client', 'foo/bar', clientApprovalRequest);

    setApproverInput(element, 'foo');

    $('input[name=acl_reason]', element).val('bar');
    browserTriggerEvent($('input[name=acl_reason]', element), 'change');

    browserTriggerEvent(
        $('input[name=cc_approval]', element).prop('checked', false),
        'change');

    $('select', element).val('reason2');
    browserTriggerEvent($('select', element), 'change');

    browserTriggerEvent($('button[name=Proceed]', element), 'click');

    expect(grrApiService.post).toHaveBeenCalledWith('foo/bar', {
      client_id: 'C:123456',
      approval: {
        reason: 'reason2',
        notified_users: ['foo'],
      },
    });
  });

  it('uses empty reason when reason is not supplied', () => {
    const element = renderTestTemplate('client');
    expect($('input[name=acl_reason]', element).val()).toEqual('');
  });

  it('suggests a reason from the scope', () => {
    const element = renderTestTemplate('client', '', '', '', 'foobar');
    expect($('input[name=acl_reason]', element).val()).toEqual('foobar');
  });

});


exports = {};
