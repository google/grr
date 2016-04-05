'use strict';

goog.require('grrUi.core.module');
goog.require('grrUi.tests.module');


describe('aff4 download link directive', function() {
  var $compile, $rootScope, $cookies;

  beforeEach(module('/static/angular-components/core/aff4-download-link.html'));
  beforeEach(module(grrUi.core.module.name));
  beforeEach(module(grrUi.tests.module.name));

  beforeEach(inject(function($injector) {
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
    $cookies = $injector.get('$cookies');
  }));

  var prevGrrState;
  beforeEach(function() {
    prevGrrState = grr.state;
    grr.state = {
      reason: 'blah'
    };
  });

  afterEach(function() {
    grr.state = prevGrrState;
  });

  var renderTestTemplate = function(aff4Path, safeExtension) {
    $rootScope.aff4Path = aff4Path;
    $rootScope.safeExtension = safeExtension;

    var template = '<grr-aff4-download-link aff4-path="aff4Path" ' +
        'safe-extension="safeExtension">some thing</grr-aff4-download-link>';
    var element = $compile(template)($rootScope);
    $rootScope.$apply();

    return element;
  };

  it('wraps nested content', function() {
    var element = renderTestTemplate(undefined, undefined);
    expect(element.text()).toContain('some thing');
  });

  it('submits a form with target=_blank on click', function() {
    var element = renderTestTemplate(undefined, undefined);

    var formSubmitted = false;
    element.find('form').submit(function(event) {
      event.preventDefault();
      formSubmitted = true;
    });

    element.find('a').click();
    expect(formSubmitted).toBe(true);
  });

  it('puts csrf token, aff4 path and reason into the form', function() {
    spyOn($cookies, 'get').and.returnValue('CSRF-TOKEN');

    var element = renderTestTemplate('aff4:/foo/bar', undefined);

    expect(element.find('input[name=csrfmiddlewaretoken]').val()).toBe(
        'CSRF-TOKEN');
    expect(element.find('input[name=aff4_path]').val()).toBe(
        'aff4:/foo/bar');
    expect(element.find('input[name=reason]').val()).toBe(
        'blah');
  });

  it('puts safe extension into form when not provided', function() {
    var element = renderTestTemplate(undefined, 'zip');

    expect(element.find('input[name=safe_extension]').val()).toBe(
        'zip');
  });
});
