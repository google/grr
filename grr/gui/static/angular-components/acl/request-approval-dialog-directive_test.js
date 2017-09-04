'use strict';

goog.require('grrUi.acl.module');
goog.require('grrUi.tests.browserTrigger');
goog.require('grrUi.tests.module');

var browserTrigger = grrUi.tests.browserTrigger;

describe('request approval dialog', function() {
  var $q, $compile, $rootScope, grrApiService, closeSpy, dismissSpy;

  beforeEach(module('/static/angular-components/acl/' +
      'request-approval-dialog.html'));
  beforeEach(module('/static/angular-components/core/' +
      'confirmation-dialog.html'));

  beforeEach(module(grrUi.acl.module.name));
  beforeEach(module(grrUi.tests.module.name));

  beforeEach(inject(function($injector) {
    $q = $injector.get('$q');
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
    grrApiService = $injector.get('grrApiService');

    closeSpy = jasmine.createSpy('close');
    dismissSpy = jasmine.createSpy('dismiss');
  }));

  var renderTestTemplate = function(
      approvalType, createUrl, createArgs, description) {
    $rootScope.approvalType = approvalType;
    $rootScope.createUrl = createUrl;
    $rootScope.createArgs = createArgs;
    $rootScope.description = description;

    $rootScope.$close = closeSpy;
    $rootScope.$dismiss = dismissSpy;

    var template = '<grr-request-approval-dialog ' +
        'approval-type="approvalType" ' +
        'create-request-url="createUrl" ' +
        'create-request-args="createArgs" ' +
        'access-error-description="description" />';

    var element = $compile(template)($rootScope);
    $rootScope.$apply();

    return element;
  };

  var clientApprovalRequest, approvals, configEntry;
  beforeEach(function() {
    clientApprovalRequest = {
      client_id: 'C:123456',
      approval: {}
    };

    approvals = {
      data: {
        items: [
          {
            type: 'ApiClientApproval',
            value: {
              reason: {
                type: 'RDFString',
                value: 'reason1'
              }
            }
          },
          {
            type: 'ApiClientApproval',
            value: {
              reason: {
                type: 'RDFString',
                value: 'reason2'
              }
            }
        }
        ]
      }
    };

    configEntry = {
      data: {
        value: {
          type: 'RDFString',
          value: 'foo@bar.com, xyz@example.com'
        }
      }
    };

    var deferred = $q.defer();
    deferred.resolve(configEntry);
    spyOn(grrApiService, 'getCached').and.returnValue(deferred.promise);

    deferred = $q.defer();
    deferred.resolve(approvals);
    spyOn(grrApiService, 'get').and.returnValue(deferred.promise);
  });

  it('shows a list of previous client reasons', function() {
    var element = renderTestTemplate('client');

    expect($('select option', element).length).toBe(3);
    expect($('select option:nth(0)', element).val()).toEqual('');
    expect($('select option:nth(1)', element).val()).toEqual('reason1');
    expect($('select option:nth(2)', element).val()).toEqual('reason2');
  });

  it('doesn\'t show a list of CC addresses when not available', function() {
    configEntry['data']['value']['value'] = undefined;
    var element = renderTestTemplate('client');

    expect(element.text()).not.toContain('CC');
    expect($('input[name=cc_approval]', element).length).toBe(0);
  });

  it('shows a list of CC addresses when they\'re available', function() {
    var element = renderTestTemplate('client');

    expect(element.text()).toContain('CC foo@bar.com, xyz@example.com');
    expect($('input[name=cc_approval]', element).length).toBe(1);
  });

  it('disables reason field when dropdown reason is selected', function() {
    var element = renderTestTemplate('client');

    $('select', element).val('reason1');
    browserTrigger($('select', element), 'change');

    expect($('input[name=acl_reason]', element).attr('disabled')).toBeTruthy();
  });

  it('doesn\'t show keep-alive checkbox for "hunt"approval type', function() {
    var element = renderTestTemplate('hunt');

    expect($('input[name=keepalive]', element).length).toBe(0);
  });

  it('shows keep-alive checkbox for "client" approval type', function() {
    var element = renderTestTemplate('client');

    expect($('input[name=keepalive]', element).length).toBe(1);
  });

  it('includes approvers into request if CC-checbox is selected', function() {
    spyOn(grrApiService, 'post').and.returnValue($q.defer().promise);

    var element = renderTestTemplate('client', 'foo/bar',
                                     clientApprovalRequest);

    $('input[name=acl_approver]', element).val('foo');
    browserTrigger($('input[name=acl_approver]', element), 'change');

    $('input[name=acl_reason]', element).val('bar');
    browserTrigger($('input[name=acl_reason]', element), 'change');

    $('input[name=cc_approval]', element).prop('checked', true);
    browserTrigger($('input[name=cc_approval]', element), 'change');

    browserTrigger($('button[name=Proceed]', element), 'click');

    expect(grrApiService.post).toHaveBeenCalledWith('foo/bar', {
      client_id: 'C:123456',
      approval: {
        reason: 'bar',
        notified_users: ['foo'],
        email_cc_addresses: ['foo@bar.com', 'xyz@example.com']
      },
      keep_client_alive: true
    });
  });

  it('includes keep_client_alive into request if checkbox is selected', function() {
    spyOn(grrApiService, 'post').and.returnValue($q.defer().promise);

    var element = renderTestTemplate('client', 'foo/bar',
                                     clientApprovalRequest);

    $('input[name=acl_approver]', element).val('foo');
    browserTrigger($('input[name=acl_approver]', element), 'change');

    $('input[name=acl_reason]', element).val('bar');
    browserTrigger($('input[name=acl_reason]', element), 'change');

    $('input[name=cc_approval]', element).prop('checked', false)
        .triggerHandler('click');
    $('input[name=keepalive]', element).prop('checked', true)
        .triggerHandler('click');

    browserTrigger($('button[name=Proceed]', element), 'click');

    expect(grrApiService.post).toHaveBeenCalledWith('foo/bar', {
      client_id: 'C:123456',
      approval: {
        reason: 'bar',
        notified_users: ['foo'],
      },
      keep_client_alive: true
    });
  });

  it('includes dropdown reason into request', function() {
    spyOn(grrApiService, 'post').and.returnValue($q.defer().promise);

    var element = renderTestTemplate('client', 'foo/bar',
                                     clientApprovalRequest);

    $('input[name=acl_approver]', element).val('foo');
    browserTrigger($('input[name=acl_approver]', element), 'change');

    $('input[name=acl_reason]', element).val('bar');
    browserTrigger($('input[name=acl_reason]', element), 'change');

    $('input[name=cc_approval]', element).prop('checked', false)
        .triggerHandler('click');

    $('select', element).val('reason2');
    browserTrigger($('select', element), 'change');

    browserTrigger($('button[name=Proceed]', element), 'click');

    expect(grrApiService.post).toHaveBeenCalledWith('foo/bar', {
      client_id: 'C:123456',
      approval: {
        reason: 'reason2',
        notified_users: ['foo'],
      },
      keep_client_alive: true
    });
  });
});
