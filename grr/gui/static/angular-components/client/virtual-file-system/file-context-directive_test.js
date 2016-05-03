'use strict';

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
    expect(controller.selectedFolderPath).toBeUndefined();
    expect(controller.selectedFilePath).toBeUndefined();
    expect(controller.selectedFileVersion).toBeUndefined();

    $rootScope.clientId = 42;
    $rootScope.selectedFolderPath = 'some/path';
    $rootScope.selectedFilePath = 'some/path/test.txt';
    $rootScope.selectedFileVersion = 1337;
    $rootScope.$apply();

    expect(controller.clientId).toEqual(42);
    expect(controller.selectedFolderPath).toEqual('some/path');
    expect(controller.selectedFilePath).toEqual('some/path/test.txt');
    expect(controller.selectedFileVersion).toEqual(1337);
  });

  it('changes the scope whenever the controller values change', function() {
    var controller = getController();

    controller.clientId = 42;
    controller.selectedFolderPath = 'some/path';
    controller.selectedFilePath = 'some/path/test.txt';
    controller.selectedFileVersion = 1337;
    $rootScope.$apply();

    expect($rootScope.clientId).toEqual(42);
    expect($rootScope.selectedFolderPath).toEqual('some/path');
    expect($rootScope.selectedFilePath).toEqual('some/path/test.txt');
    expect($rootScope.selectedFileVersion).toEqual(1337);
  });

  it('sets the selected file when only the selected folder is set', function() {
    var controller = getController();

    controller.selectedFolderPath = 'some/path';
    controller.selectedFilePath = null;
    $rootScope.$apply();

    expect($rootScope.selectedFolderPath).toEqual('some/path');
    expect($rootScope.selectedFilePath).toEqual('some/path');
  });

  it('allows settings the selected folder via selectFolder', function() {
    var controller = getController();

    controller.selectFolder('some/path');
    $rootScope.$apply();

    expect($rootScope.selectedFolderPath).toEqual('some/path');
    expect($rootScope.selectedFilePath).toEqual('some/path');
    expect($rootScope.selectedFileVersion).toBeNull();

    controller.selectFolder('some/other/path', 1337);
    $rootScope.$apply();

    expect($rootScope.selectedFolderPath).toEqual('some/other/path');
    expect($rootScope.selectedFilePath).toEqual('some/other/path');
    expect($rootScope.selectedFileVersion).toEqual(1337);
  });

  it('allows settings the selected file via selectFile', function() {
    var controller = getController();

    controller.selectedFolderPath = 'some/path';
    controller.selectFile('some/path/test.txt');
    $rootScope.$apply();

    expect($rootScope.selectedFolderPath).toEqual('some/path');
    expect($rootScope.selectedFilePath).toEqual('some/path/test.txt');
    expect($rootScope.selectedFileVersion).toBeNull();

    controller.selectFile('some/other/path/test.txt', 1337);
    $rootScope.$apply();

    expect($rootScope.selectedFolderPath).toEqual('some/path');
    expect($rootScope.selectedFilePath).toEqual('some/other/path/test.txt');
    expect($rootScope.selectedFileVersion).toEqual(1337);
  });

});