'use strict';

goog.require('grrUi.core.module');
goog.require('grrUi.tests.module');

var browserTrigger = grrUi.tests.browserTrigger;

describe('confirmation dialog directive', function() {
  var $compile, $rootScope, $q;

  beforeEach(module('/static/angular-components/core/confirmation-dialog.html'));
  beforeEach(module(grrUi.core.module.name));
  beforeEach(module(grrUi.tests.module.name));

  beforeEach(inject(function($injector) {
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
    $q = $injector.get('$q');
  }));

  var render = function(title, message, proceedCallback) {
    $rootScope.title = title;
    $rootScope.message = message;
    $rootScope.proceed = proceedCallback;

    var template = '<grr-confirmation-dialog ' +
                   '    title="title" ' +
                   '    proceed="proceed()">' +
                   '  {$ message $}' +
                   '</grr-confirmation-dialog>';
    var element = $compile(template)($rootScope);
    $rootScope.$apply();

    return element;
  };

  it('shows title and message', function() {
    var title = 'Test Title';
    var message = 'Test Content Message';
    var element = render(title, message);
    expect(element.find('.modal-header h3').text().trim()).toBe(title);
    expect(element.find('.modal-body').text().trim()).toContain(message);
  });

  it('shows success on proceed promise resolve', function() {
    var successMessage = 'Some action just happened successfully';
    var proceed = function(){
      return $q.when(successMessage);
    };
    var element = render('', '', proceed);
    spyOn($rootScope, 'proceed').and.callThrough();

    // check proceed() was clicked and shows the success message
    browserTrigger(element.find('button[name="Proceed"]'), 'click');
    $rootScope.$apply();

    expect($rootScope.proceed).toHaveBeenCalled();
    expect(element.find('.modal-body .alert-success').text().trim()).toBe(successMessage);
    expect(element.find('button[name="Close"]').length).toBe(1);
  });

  it('shows error on proceed promise reject', function() {
    var errorMessage = 'Some action could not be performed';
    var proceed = function(){
      return $q.reject(errorMessage);
    };
    var element = render('', '', proceed);

    spyOn($rootScope, 'proceed').and.callThrough();
    browserTrigger(element.find('button[name="Proceed"]'), 'click');
    $rootScope.$apply();

    expect($rootScope.proceed).toHaveBeenCalled();
    expect(element.find('.modal-body .alert-danger').text().trim()).toBe(errorMessage);
  });

  it('shows a disabled proceed button when canProceed is false', function() {
    var buttonEnabled = false;
    $rootScope.canProceed = function() {
      return buttonEnabled;
    };
    var template = '<grr-confirmation-dialog can-proceed="canProceed()">' +
                   '</grr-confirmation-dialog>';
    var element = $compile(template)($rootScope);
    $rootScope.$apply();

    expect($('button[name=Proceed][disabled]', element).length).toBe(1);
    buttonEnabled = true;
    $rootScope.$apply();
    expect($('button[name=Proceed][disabled]', element).length).toBe(0);
  });
  // someDDirectiveName  -> some-d-directive-name
  // someDDDirectiveName -> some-d-d-directive-name
  // someADirectiveName  -> some-a-directive-name
});
