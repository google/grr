'use strict';

goog.require('grrUi.core.module');
goog.require('grrUi.tests.module');


describe('download collection files directive', function() {
  var $compile, $q, $rootScope, grrApiService;

  var $window = {
    navigator: {
    }
  };
  beforeEach(module(function($provide) {
    $provide.value('$window', $window);
  }));

  beforeEach(module('/static/angular-components/core/' +
      'download-collection-files.html'));
  beforeEach(module(grrUi.core.module.name));
  beforeEach(module(grrUi.tests.module.name));

  beforeEach(inject(function($injector) {
    $compile = $injector.get('$compile');
    $q = $injector.get('$q');
    $rootScope = $injector.get('$rootScope');
    grrApiService = $injector.get('grrApiService');
  }));

  var renderTestTemplate = function(opt_withExportCommand) {
    $rootScope.downloadUrl = 'some/download/url';
    if (opt_withExportCommand) {
      $rootScope.exportCommandUrl = 'some/export-command/url';
    }

    var template = '<grr-download-collection-files ' +
        'download-url="downloadUrl" export-command-url="exportCommandUrl" />';
    var element = $compile(template)($rootScope);
    $rootScope.$apply();

    return element;
  };

  it('shows TAR.GZ as default option on Mac', function() {
    $window.navigator.appVersion = 'Mac';

    var element = renderTestTemplate();
    expect(element.find('button').text()).toContain('Generate TAR.GZ');
    expect(element.find('ul.dropdown-menu li').text()).toContain(
        'Generate ZIP');
  });

  it('shows ZIP as default option on Linux', function() {
    $window.navigator.appVersion = 'Linux';

    var element = renderTestTemplate();
    expect(element.find('button').text()).toContain('Generate ZIP');
    expect(element.find('ul.dropdown-menu li').text()).toContain(
        'Generate TAR.GZ');
  });

  it('sends TAR.GZ generation request when button clicked on Mac', function() {
    $window.navigator.appVersion = 'Mac';

    var deferred = $q.defer();
    spyOn(grrApiService, 'downloadFile').and.returnValue(deferred.promise);

    var element = renderTestTemplate();
    element.find('button').click();

    expect(grrApiService.downloadFile).toHaveBeenCalledWith(
        'some/download/url', {archive_format: 'TAR_GZ'});
  });

  it('sends ZIP generation request when dropdownclicked on Mac', function() {
    $window.navigator.appVersion = 'Mac';

    var deferred = $q.defer();
    spyOn(grrApiService, 'downloadFile').and.returnValue(deferred.promise);

    var element = renderTestTemplate();
    element.find('ul.dropdown-menu li a').click();

    expect(grrApiService.downloadFile).toHaveBeenCalledWith(
        'some/download/url', {archive_format: 'ZIP'});
  });

  it('sends ZIP generation request when button is clicked on Linux',
     function() {
    $window.navigator.appVersion = 'Linux';

    var deferred = $q.defer();
    spyOn(grrApiService, 'downloadFile').and.returnValue(deferred.promise);

    var element = renderTestTemplate();
    element.find('button').click();

    expect(grrApiService.downloadFile).toHaveBeenCalledWith(
        'some/download/url', {archive_format: 'ZIP'});
  });

  it('sends TAR.GZ generation request when dropdown clicked on Linux',
     function() {
    $window.navigator.appVersion = 'Linux';

    var deferred = $q.defer();
    spyOn(grrApiService, 'downloadFile').and.returnValue(deferred.promise);

    var element = renderTestTemplate();
    element.find('ul.dropdown-menu li a').click();

    expect(grrApiService.downloadFile).toHaveBeenCalledWith(
        'some/download/url', {archive_format: 'TAR_GZ'});
  });

  it('disables the button after request is sent', function() {
    var deferred = $q.defer();
    spyOn(grrApiService, 'downloadFile').and.returnValue(deferred.promise);

    var element = renderTestTemplate();
    expect(element.find('button[disabled]').length).toBe(0);

    element.find('ul.dropdown-menu li a').click();

    expect(element.find('button[disabled]').length).not.toBe(0);
  });

  it('shows success message if request succeeds', function() {
    var deferred = $q.defer();
    spyOn(grrApiService, 'downloadFile').and.returnValue(deferred.promise);

    var element = renderTestTemplate();
    element.find('button').click();

    deferred.resolve({status: 'OK'});
    $rootScope.$apply();

    expect(element.text()).toContain('Generation has started.');
  });

  it('shows failure message if request fails', function() {
    var deferred = $q.defer();
    spyOn(grrApiService, 'downloadFile').and.returnValue(deferred.promise);

    var element = renderTestTemplate();
    element.find('button').click();

    deferred.reject({data: {message: 'FAIL'}});
    $rootScope.$apply();

    expect(element.text()).toContain('Can\'t generate archive: FAIL');
  });

  describe('with export command url provided', function() {
    var exportCommandDeferred;

    beforeEach(function() {
      $window.navigator.appVersion = 'Mac';

      exportCommandDeferred = $q.defer();
      spyOn(grrApiService, 'get').and.returnValue(
          exportCommandDeferred.promise);
    });

    it('fetches export command', function() {
      var element = renderTestTemplate(true);
      expect(grrApiService.get).toHaveBeenCalledWith('some/export-command/url');
    });

    it('shows "Show GRR export tool command" link', function() {
      exportCommandDeferred.resolve({
        data: {
          command: 'blah --foo'
        }
      });
      var element = renderTestTemplate(true);
      expect($('a:contains("Show GRR export tool command")', element).length)
          .toBe(1);
    });

    it('renders export command', function() {
      exportCommandDeferred.resolve({
        data: {
          command: 'blah --foo'
        }
      });
      var element = renderTestTemplate(true);

      expect($('pre:contains("blah --foo")', element).length).toBe(1);
    });
  });
});
