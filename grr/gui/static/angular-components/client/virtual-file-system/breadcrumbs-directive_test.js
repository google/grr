'use strict';

goog.module('grrUi.client.virtualFileSystem.breadcrumbsDirectiveTest');

const {browserTriggerEvent, testsModule} = goog.require('grrUi.tests');
const {clientModule} = goog.require('grrUi.client.client');


describe('breadcrums directive', () => {
  let $compile;
  let $rootScope;
  let $scope;


  beforeEach(module('/static/angular-components/client/virtual-file-system/breadcrumbs.html'));
  beforeEach(module(clientModule.name));
  beforeEach(module(testsModule.name));

  beforeEach(inject(($injector) => {
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
    $scope = $rootScope.$new();
  }));

  const render = (path, stripEndingSlash) => {
    $scope.obj = {
      // We need to pass an object to see changes.
      path: path,
      stripEndingSlash: stripEndingSlash,
    };

    const template =
        '<grr-breadcrumbs strip-ending-slash="obj.stripEndingSlash" ' +
        'path="obj.path" />';
    const element = $compile(template)($scope);
    $scope.$apply();

    return element;
  };

  it('should show the path components as links', () => {
    const element = render('path/to/some/resource');

    // Last component is dropped as it points to a file. Therefore there
    // should be 2 links: "path" and "to". And "some" should be a
    // non-link element with class .active.
    expect(element.find('a').length).toBe(2);
    expect(element.find('li.active').text().trim()).toBe('some');
  });

  it('strips ending slash if strip-ending-slash is true', () => {
    const element = render('path/to/some/resource/', true);

    // Ending slash is stripped, so behaviour should be similar to the
    // one with render('path/to/some/resource').
    expect(element.find('a').length).toBe(2);
    expect(element.find('li.active').text().trim()).toBe('some');
  });

  it('should change the path when a link is clicked', () => {
    const element = render('path/to/some/resource');
    const links = element.find('a');

    expect(links.length).toBe(2);
    browserTriggerEvent(links[1], 'click');
    $scope.$apply();

    expect(element.find('li.active').text().trim()).toBe('to');
    expect($scope.obj.path).toBe('path/to/');
  });

  it('should change the links when the scope changes', () => {
    const element = render('path/to/some/resource');

    expect(element.find('a').length).toBe(2);
    expect(element.find('li.active').text().trim()).toBe('some');

    $scope.obj.path = "a/path/to/another/file";
    $scope.$apply();
    expect(element.find('a').length).toBe(3);
    expect(element.find('li.active').text().trim()).toBe('another');
  });
});


exports = {};
