'use strict';

goog.provide('grrUi.core.versionDropdownDirectiveTest');
goog.require('grrUi.core.module');
goog.require('grrUi.core.versionDropdownDirective.VersionDropdownDirective');
goog.require('grrUi.tests.module');

describe('version dropdown directive', function () {
  var $compile, $rootScope, $scope, $q, grrApiService;

  var REFRESH_VERSIONS_EVENT =
      grrUi.core.versionDropdownDirective.VersionDropdownDirective.REFRESH_VERSIONS_EVENT;

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

  it('shows HEAD as the first element in the versions list', function() {
    mockApiService({
      'some/url': [{value: 10}]
    });

    var element = render('some/url');
    expect(element.find('option').length).toBe(2);
    expect(element.find('option:nth(0)').val()).toBe('HEAD');
  });

  it('selects HEAD if not version specified', function() {
    mockApiService({
      'some/url': [{value: 10}]
    });

    var element = render('some/url');
    expect(element.find('option[selected]').val()).toBe('HEAD');
  });

  it('should show all versions from server and select the passed one', function () {
    mockApiService({
      'some/url': [{value: 10}, {value: 42}, {value: 50}]
    });

    var element = render('some/url', 42);
    expect(element.find('option').length).toBe(4);  // 3 versions + HEAD
    expect(element.find('option[selected]').val()).toBe('42');
    expect($scope.version.data).toBe(42);
  });

  it('should show add current version to the server versions list', function () {
    mockApiService({
      'some/url': [{value: 10}, {value: 41}, {value: 50}]
    });

    var element = render('some/url', 42);

    // 3 versions from server + selected version + HEAD
    expect(element.find('option').length).toBe(5);

    expect(element.find('option[selected]').val()).toBe('42');
    expect($scope.version.data).toBe(42);
  });

  it('shows hint when a version other than the latest is shown', function () {
    mockApiService({
      'some/url': [{value: 10}, {value: 42}, {value: 50}]
    });

    var element = render('some/url', 42);
    expect(element.find('.newer-version-hint').length).toBe(1);
  });

  it('does not show a hint when a newest version  is shown', function () {
    mockApiService({
      'some/url': [{value: 10}, {value: 42}, {value: 50}]
    });

    var element = render('some/url', 50);
    expect(element.find('.newer-version-hint').length).toBe(0);
  });

  it('should update the selected option on scope value change', function () {
    mockApiService({
      'some/url': [{value: 10}, {value: 42}, {value: 50}]
    });

    var element = render('some/url', 42);
    expect(element.find('option').length).toBe(4);
    expect(element.find('option[selected]').val()).toBe('42');
    expect($scope.version.data).toBe(42);

    $scope.version.data = 50;
    $scope.$apply();
    expect(element.find('option').length).toBe(4);
    expect(element.find('option[selected]').val()).toBe('50');

    $scope.version.data = 99;
    $scope.$apply();
    // This version is not in the server-provided list, so the list should be
    // extended.
    expect(element.find('option').length).toBe(5);
    expect(element.find('option[selected]').val()).toBe('99');
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

  it('should fetch versions again when a REFRESH_VERSIONS_EVENT is broadcasted', function () {
    var items = [];
    mockApiService({
      'some/url': items
    });

    var element = render('some/url');
    expect(element.find('select[disabled]').length).toBe(1);
    expect(element.find('option[selected]').text().trim()).toBe('No versions available.');

    // Broadcast REFRESH_VERSIONS_EVENT and check that there are options now.
    items.push({value: 10});
    items.push({value: 42});
    $rootScope.$broadcast(REFRESH_VERSIONS_EVENT, {});
    $rootScope.$apply();

    expect(element.find('select[disabled]').length).toBe(0);
    expect(element.find('option').length).toBe(3);
    expect(element.find('option[selected]').val()).toBe('HEAD');
    expect($scope.version.data).toBeUndefined(); // It does not change the model.
  });

});
