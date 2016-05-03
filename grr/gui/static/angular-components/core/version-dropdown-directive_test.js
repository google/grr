'use strict';

goog.require('grrUi.core.module');
goog.require('grrUi.tests.module');

describe('version dropdown directive', function () {
  var $compile, $rootScope, $scope, $q, grrApiService;

  beforeEach(module('/static/angular-components/core/version-dropdown.html'));
  beforeEach(module(grrUi.core.module.name));
  beforeEach(module(grrUi.tests.module.name));

  beforeEach(inject(function ($injector) {
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
    $q = $injector.get('$q');
    grrApiService = $injector.get('grrApiService');
    $scope = $rootScope.$new();
  }));

  var render = function (url, version) {
    $scope.url = url;
    $scope.version = { // We need to pass an object to see changes.
      data: version
    };

    var template = '<grr-version-dropdown url="url" version="version.data" />';
    var element = $compile(template)($scope);
    $scope.$apply();

    return element;
  };

  var mockApiService = function(responses) {
    spyOn(grrApiService, 'get').and.callFake(function(path) {
      var response = { times: responses[path] }; // Wrap return value in type structure.
      return $q.when({ data: response });
    });
  };

  it('should show all versions from server and select the passed one', function () {
    mockApiService({
      'some/url': [{value: 10}, {value: 42}, {value: 50}]
    });

    var element = render('some/url', 42);
    expect(element.find('option').length).toBe(3);
    expect(element.find('option[selected]').val()).toBe('42');
    expect($scope.version.data).toBe(42);
  });

  it('should keep the selection if it is not in the version list', function () {
    mockApiService({
      'some/url': [{value: 10}]
    });

    var element = render('some/url', 42);
    expect(element.find('option').length).toBe(2); // Option for 10 and empty option for the selection.
    expect(element.find('option[selected]').val()).toBeUndefined();
    expect($scope.version.data).toBe(42);
  });

  it('shows hint when a version other than the latest is shown', function () {
    mockApiService({
      'some/url': [{value: 10}, {value: 42}, {value: 50}]
    });

    var element = render('some/url', 42);
    expect(element.find('.newer-version-hint').length).toBe(1);

    var element = render('some/url', 10);
    expect(element.find('.newer-version-hint').length).toBe(0);
  });

  it('should update the selected option on scope value change', function () {
    mockApiService({
      'some/url': [{value: 10}, {value: 42}, {value: 50}]
    });

    var element = render('some/url', 42);
    expect(element.find('option').length).toBe(3);
    expect(element.find('option[selected]').val()).toBe('42');
    expect($scope.version.data).toBe(42);

    $scope.version.data = 50;
    $scope.$apply();
    expect(element.find('option').length).toBe(3);
    expect(element.find('option[selected]').val()).toBe('50');

    $scope.version.data = 99;
    $scope.$apply();
    expect(element.find('option').length).toBe(4);
    expect(element.find('option[selected]').val()).toBeUndefined();
  });

  it('should be disabled when no options are available', function () {
    mockApiService({
      'some/url': []
    });

    var element = render('some/url', 42);
    expect(element.find('select[disabled]').length).toBe(1);
    expect(element.find('option[selected]').text().trim()).toBe('No versions available.');
    expect($scope.version.data).toBe(42); // It does not change the model.
  });

});
