'use strict';

goog.require('grrUi.client.module');
goog.require('grrUi.tests.browserTrigger');
goog.require('grrUi.tests.module');

var browserTrigger = grrUi.tests.browserTrigger;

describe('breadcrums directive', function () {
  var $compile, $rootScope, $scope;

  beforeEach(module('/static/angular-components/client/virtual-file-system/breadcrumbs.html'));
  beforeEach(module(grrUi.client.module.name));
  beforeEach(module(grrUi.tests.module.name));

  beforeEach(inject(function ($injector) {
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
    $scope = $rootScope.$new();
  }));

  var render = function (path) {
    $scope.obj = { // We need to pass an object to see changes.
      path: path
    };

    var template = '<grr-breadcrumbs path="obj.path" />';
    var element = $compile(template)($scope);
    $scope.$apply();

    return element;
  };

  it('should show the path components as links', function () {
    var element = render('path/to/some/resource');
    expect(element.find('a').length).toBe(3);
    expect(element.find('li.active').text().trim()).toBe('resource');
  });

  it('should change the path when a link is clicked', function () {
    var element = render('path/to/some/resource');
    var links = element.find('a');

    expect(links.length).toBe(3);
    browserTrigger(links[2], 'click');
    $scope.$apply();

    expect(element.find('li.active').text().trim()).toBe('some');
    expect($scope.obj.path).toBe('path/to/some');
  });

  it('should change the links when the scope changes', function () {
    var element = render('path/to/some/resource');

    expect(element.find('a').length).toBe(3);
    expect(element.find('li.active').text().trim()).toBe('resource');

    $scope.obj.path = "a/path/to/another/file";
    $scope.$apply();
    expect(element.find('a').length).toBe(4);
    expect(element.find('li.active').text().trim()).toBe('file');
  });

});
