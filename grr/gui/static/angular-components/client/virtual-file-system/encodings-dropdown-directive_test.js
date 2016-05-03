'use strict';

goog.require('grrUi.client.module');
goog.require('grrUi.tests.browserTrigger');
goog.require('grrUi.tests.module');

var browserTrigger = grrUi.tests.browserTrigger;

describe('encodings dropdown directive', function () {
  var $compile, $rootScope, $scope, $q, grrApiService;

  beforeEach(module('/static/angular-components/client/virtual-file-system/encodings-dropdown.html'));
  beforeEach(module(grrUi.client.module.name));
  beforeEach(module(grrUi.tests.module.name));

  beforeEach(inject(function ($injector) {
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
    $q = $injector.get('$q');
    grrApiService = $injector.get('grrApiService');
    $scope = $rootScope.$new();
  }));

  var mockApiService = function(responses) {
    spyOn(grrApiService, 'get').and.callFake(function(path) {
      var response = { encodings: responses[path] }; // Wrap return value in type structure.
      return $q.when({ data: response });
    });
  };

  var render = function (encoding) {
    $scope.obj = { // We need to pass an object to see changes.
      encoding: encoding
    };

    var template = '<grr-encodings-dropdown encoding="obj.encoding" />';
    var element = $compile(template)($scope);
    $scope.$apply();

    return element;
  };

  it('should select the scope value', function () {
    var encodings = [{value: 'ENC1'}, {value: 'ENC2'}, {value: 'ENC99'}, {value: 'UTF_8'}];
    mockApiService({
      'reflection/file-encodings': encodings
    });

    var element = render('ENC1');
    expect(element.find('option').length).toBe(4);
    expect(element.find('option[selected]').text().trim()).toBe('ENC1');
    expect(grrApiService.get).toHaveBeenCalled();
  });

  it('should change the selection when the scope changes', function () {
    var encodings = [{value: 'ENC1'}, {value: 'ENC2'}, {value: 'ENC99'}, {value: 'UTF_8'}];
    mockApiService({
      'reflection/file-encodings': encodings
    });

    var element = render('ENC1');
    expect(element.find('option[selected]').text().trim()).toBe('ENC1');

    $scope.obj.encoding = 'UTF_8';
    $scope.$apply();
    expect(element.find('option[selected]').text().trim()).toBe('UTF_8');
  });

  it('should be disabled when no options are available', function () {
    mockApiService({
      'some/url': []
    });

    var element = render('UTF_8');
    expect(element.find('select[disabled]').length).toBe(1);
    expect(element.find('option[selected]').text().trim()).toBe('No encodings available.');
    expect($scope.obj.encoding).toBe('UTF_8'); // It does not change the model.
  });

});
