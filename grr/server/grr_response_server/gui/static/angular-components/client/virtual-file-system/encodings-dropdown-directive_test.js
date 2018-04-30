'use strict';

goog.module('grrUi.client.virtualFileSystem.encodingsDropdownDirectiveTest');

const {clientModule} = goog.require('grrUi.client.client');
const {testsModule} = goog.require('grrUi.tests');


describe('encodings dropdown directive', () => {
  let $compile;
  let $q;
  let $rootScope;
  let $scope;
  let grrApiService;


  beforeEach(module('/static/angular-components/client/virtual-file-system/encodings-dropdown.html'));
  beforeEach(module(clientModule.name));
  beforeEach(module(testsModule.name));

  beforeEach(inject(($injector) => {
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
    $q = $injector.get('$q');
    grrApiService = $injector.get('grrApiService');
    $scope = $rootScope.$new();
  }));

  const mockApiService = (responses) => {
    spyOn(grrApiService, 'get').and.callFake((path) => {
      const response = {
        encodings: responses[path]
      };  // Wrap return value in type structure.
      return $q.when({ data: response });
    });
  };

  const render = (encoding) => {
    $scope.obj = {
      // We need to pass an object to see changes.
      encoding: encoding,
    };

    const template = '<grr-encodings-dropdown encoding="obj.encoding" />';
    const element = $compile(template)($scope);
    $scope.$apply();

    return element;
  };

  it('should select the scope value', () => {
    const encodings =
        [{value: 'ENC1'}, {value: 'ENC2'}, {value: 'ENC99'}, {value: 'UTF_8'}];
    mockApiService({
      'reflection/file-encodings': encodings,
    });

    const element = render('ENC1');
    expect(element.find('option').length).toBe(4);
    expect(element.find('option[selected]').text().trim()).toBe('ENC1');
    expect(grrApiService.get).toHaveBeenCalled();
  });

  it('should change the selection when the scope changes', () => {
    const encodings =
        [{value: 'ENC1'}, {value: 'ENC2'}, {value: 'ENC99'}, {value: 'UTF_8'}];
    mockApiService({
      'reflection/file-encodings': encodings,
    });

    const element = render('ENC1');
    expect(element.find('option[selected]').text().trim()).toBe('ENC1');

    $scope.obj.encoding = 'UTF_8';
    $scope.$apply();
    expect(element.find('option[selected]').text().trim()).toBe('UTF_8');
  });

  it('should be disabled when no options are available', () => {
    mockApiService({
      'some/url': [],
    });

    const element = render('UTF_8');
    expect(element.find('select[disabled]').length).toBe(1);
    expect(element.find('option').text().trim()).toBe('No encodings available.');
    expect($scope.obj.encoding).toBe('UTF_8'); // It does not change the model.
  });
});


exports = {};
