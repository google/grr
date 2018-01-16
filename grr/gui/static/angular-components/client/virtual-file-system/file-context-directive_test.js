'use strict';

goog.provide('grrUi.client.virtualFileSystem.fileContextDirectiveTest');
goog.require('grrUi.client.virtualFileSystem.fileContextDirective.FileContextController');


describe('file context directive', function() {
  var $rootScope;

  beforeEach(inject(function($injector) {
    $rootScope = $injector.get('$rootScope');
  }));

  var getController = function() {
    var controller;

    inject(function($injector) {
      controller = $injector.instantiate(
          grrUi.client.virtualFileSystem.fileContextDirective.FileContextController,
          {
            '$scope': $rootScope
          });
    });
    // We need to set the controller instance on the scope, so that the watchers apply.
    $rootScope.controller = controller;
    $rootScope.$apply();

    return controller;
  };

  it('changes the controller values when the scope values change', function() {
    var controller = getController();

    expect(controller.clientId).toBeUndefined();
    expect(controller.selectedFilePath).toBeUndefined();
    expect(controller.selectedFileVersion).toBeUndefined();

    $rootScope.clientId = 42;
    $rootScope.selectedFilePath = 'some/path/test.txt';
    $rootScope.selectedFileVersion = 1337;
    $rootScope.$apply();

    expect(controller.clientId).toEqual(42);
    expect(controller.selectedFilePath).toEqual('some/path/test.txt');
    expect(controller.selectedFileVersion).toEqual(1337);
  });

  it('changes the scope whenever the controller values change', function() {
    var controller = getController();

    controller.clientId = 42;
    controller.selectedFilePath = 'some/path/test.txt';
    controller.selectedFileVersion = 1337;
    $rootScope.$apply();

    expect($rootScope.clientId).toEqual(42);
    expect($rootScope.selectedFilePath).toEqual('some/path/test.txt');
    expect($rootScope.selectedFileVersion).toEqual(1337);
  });

  it('allows settings the selected file via selectFile', function() {
    var controller = getController();

    controller.selectFile('some/path/test.txt');
    $rootScope.$apply();

    expect($rootScope.selectedFilePath).toEqual('some/path/test.txt');
    expect($rootScope.selectedFileVersion).toBeNull();

    controller.selectFile('some/other/path/test.txt', 1337);
    $rootScope.$apply();

    expect($rootScope.selectedFilePath).toEqual('some/other/path/test.txt');
    expect($rootScope.selectedFileVersion).toEqual(1337);
  });

});
