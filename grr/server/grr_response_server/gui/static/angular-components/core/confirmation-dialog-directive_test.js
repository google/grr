'use strict';

goog.module('grrUi.core.confirmationDialogDirectiveTest');

const {browserTriggerEvent, testsModule} = goog.require('grrUi.tests');
const {coreModule} = goog.require('grrUi.core.core');


describe('confirmation dialog directive', () => {
  let $compile;
  let $q;
  let $rootScope;


  beforeEach(module('/static/angular-components/core/confirmation-dialog.html'));
  beforeEach(module(coreModule.name));
  beforeEach(module(testsModule.name));

  beforeEach(inject(($injector) => {
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
    $q = $injector.get('$q');
  }));

  const render = (title, message, proceedCallback, buttonClass) => {
    $rootScope.title = title;
    $rootScope.message = message;
    $rootScope.proceed = proceedCallback;
    $rootScope.buttonClass = buttonClass;

    const template = '<grr-confirmation-dialog ' +
        '    title="title" ' +
        '    proceed="proceed()"' +
        '    proceed-class="buttonClass">' +
        '  {$ message $}' +
        '</grr-confirmation-dialog>';
    const element = $compile(template)($rootScope);
    $rootScope.$apply();

    return element;
  };

  it('shows title and message', () => {
    const title = 'Test Title';
    const message = 'Test Content Message';
    const element = render(title, message);
    expect(element.find('.modal-header h3').text().trim()).toBe(title);
    expect(element.find('.modal-body').text().trim()).toContain(message);
  });

  it('applies given style to "proceed" button', () => {
    const element = render('title', 'message', undefined, 'btn-warning');
    expect(element.find('button.btn-warning')).not.toBe(undefined);
  });

  it('shows success on proceed promise resolve', () => {
    const successMessage = 'Some action just happened successfully';
    const proceed = (() => $q.when(successMessage));
    const element = render('', '', proceed);
    spyOn($rootScope, 'proceed').and.callThrough();

    // check proceed() was clicked and shows the success message
    browserTriggerEvent(element.find('button[name="Proceed"]'), 'click');
    $rootScope.$apply();

    expect($rootScope.proceed).toHaveBeenCalled();
    expect(element.find('.modal-footer .text-success').text().trim()).toBe(successMessage);
    expect(element.find('button[name="Close"]').length).toBe(1);
  });

  it('shows error on proceed promise reject', () => {
    const errorMessage = 'Some action could not be performed';
    const proceed = (() => $q.reject(errorMessage));
    const element = render('', '', proceed);

    spyOn($rootScope, 'proceed').and.callThrough();
    browserTriggerEvent(element.find('button[name="Proceed"]'), 'click');
    $rootScope.$apply();

    expect($rootScope.proceed).toHaveBeenCalled();
    expect(element.find('.modal-footer .text-danger').text().trim()).toBe(errorMessage);
  });

  it('shows a disabled proceed button when canProceed is false', () => {
    let buttonEnabled = false;
    $rootScope.canProceed = (() => buttonEnabled);
    const template = '<grr-confirmation-dialog can-proceed="canProceed()">' +
        '</grr-confirmation-dialog>';
    const element = $compile(template)($rootScope);
    $rootScope.$apply();

    expect($('button[name=Proceed][disabled]', element).length).toBe(1);
    buttonEnabled = true;
    $rootScope.$apply();
    expect($('button[name=Proceed][disabled]', element).length).toBe(0);
  });
});


exports = {};
