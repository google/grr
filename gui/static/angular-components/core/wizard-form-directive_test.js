'use strict';

goog.require('grrUi.core.module');
goog.require('grrUi.tests.module');

describe('grr-wizard-form directive', function() {
  var $compile, $rootScope;

  beforeEach(module('/static/angular-components/core/wizard-form.html'));
  beforeEach(module('/static/angular-components/core/wizard-form-page.html'));
  beforeEach(module(grrUi.core.module.name));
  beforeEach(module(grrUi.tests.module.name));

  beforeEach(inject(function($injector) {
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
  }));

  var renderTestTemplate = function(template) {
    if (angular.isUndefined(template)) {
      template = '<grr-wizard-form title="Test wizard form" ' +
          'on-resolve="resolved = true" on-reject="rejected = true">' +

          '<grr-wizard-form-page title="Page 1" next-button-label="go on!">' +
          'foo</grr-wizard-form-page>' +

          '<grr-wizard-form-page title="Page 2" prev-button-label="go back!">' +
          'bar</grr-wizard-form-page>' +

          '</grr-wizard-form>';
    }

    var element = $compile(template)($rootScope);
    $rootScope.$apply();

    return element;
  };

  it('shows first page by default', function() {
    var element = renderTestTemplate();

    expect(element.text()).toContain('Page 1');
    expect(element.text()).not.toContain('Page 2');
  });

  it('clicking on "Next" button shows next page', function() {
    var element = renderTestTemplate();

    browserTrigger(element.find('button.Next'), 'click');

    expect(element.text()).toContain('Page 2');
    expect(element.text()).not.toContain('Page 1');
  });

  it('clicking on "Back" button shows previous page', function() {
    var element = renderTestTemplate();

    browserTrigger(element.find('button.Next'), 'click');
    browserTrigger(element.find('button.Back'), 'click');

    expect(element.text()).toContain('Page 1');
    expect(element.text()).not.toContain('Page 2');
  });

  it('hides "Back" button on the first page', function() {
    var element = renderTestTemplate();

    expect(element.find('button.Back[disabled]').length).toBe(0);
  });

  it('shows "Back" button on the second page', function() {
    var element = renderTestTemplate();

    browserTrigger(element.find('button.Next'), 'click');

    expect(element.find('button.Back[disabled]').length).toBe(0);
  });

  it('hides "Back" button if page\'s noBackButton is true', function() {
    var element = renderTestTemplate('<grr-wizard-form>' +
        '<grr-wizard-form-page title="Page 1">foo</grr-wizard-form-page>' +
        '<grr-wizard-form-page title="Page 2" no-back-button="flag">bar' +
        '</grr-wizard-form-page>' +
        '</grr-wizard-form>');

    browserTrigger(element.find('button.Next'), 'click');
    expect(element.find('button.Back').length).toBe(1);

    $rootScope.flag = true;
    $rootScope.$apply();

    expect(element.find('button.Back').length).toBe(0);
  });

  it('disables "Next" button if current page reports as invalid', function() {
    var element = renderTestTemplate('<grr-wizard-form>' +
        '<grr-wizard-form-page title="Page 1" is-valid="flag">foo' +
        '</grr-wizard-form-page>' +
        '</grr-wizard-form>');

    expect(element.find('button.Next[disabled]').length).toBe(1);

    $rootScope.flag = true;
    $rootScope.$apply();

    expect(element.find('button.Next:not([disabled])').length).toBe(1);
  });

  it('takes "Back" button label from page settings', function() {
    var element = renderTestTemplate();

    browserTrigger(element.find('button.Next'), 'click');

    expect(element.find('button.Back').text().trim()).toBe('go back!');
  });

  it('takes "Next" button label from page settings', function() {
    var element = renderTestTemplate();

    expect(element.find('button.Next').text().trim()).toBe('go on!');
  });

  it('calls "on-resolve" when "Next" is clicked on last page', function() {
    var element = renderTestTemplate();

    expect($rootScope.resolved).toBeUndefined();

    browserTrigger(element.find('button.Next'), 'click');
    expect($rootScope.resolved).toBeUndefined();

    browserTrigger(element.find('button.Next'), 'click');
    expect($rootScope.resolved).toBe(true);
  });

  it('calls "on-reject" when "x" is clicked', function() {
    var element = renderTestTemplate();

    expect($rootScope.rejected).toBeUndefined();

    browserTrigger(element.find('button.close'), 'click');
    expect($rootScope.rejected).toBe(true);
  });

});
