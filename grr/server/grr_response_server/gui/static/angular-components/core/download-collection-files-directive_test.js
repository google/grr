'use strict';

goog.module('grrUi.core.downloadCollectionFilesDirectiveTest');

const {coreModule} = goog.require('grrUi.core.core');
const {testsModule} = goog.require('grrUi.tests');


describe('download collection files directive', () => {
  let $compile;
  let $q;
  let $rootScope;
  let grrApiService;


  const $window = {
    navigator: {},
  };
  beforeEach(module(($provide) => {
    $provide.value('$window', $window);
  }));

  beforeEach(module('/static/angular-components/core/' +
      'download-collection-files.html'));
  beforeEach(module(coreModule.name));
  beforeEach(module(testsModule.name));

  beforeEach(inject(($injector) => {
    $compile = $injector.get('$compile');
    $q = $injector.get('$q');
    $rootScope = $injector.get('$rootScope');
    grrApiService = $injector.get('grrApiService');
  }));

  const renderTestTemplate = (opt_withExportCommand) => {
    $rootScope.downloadUrl = 'some/download/url';
    if (opt_withExportCommand) {
      $rootScope.exportCommandUrl = 'some/export-command/url';
    }

    const template = '<grr-download-collection-files ' +
        'download-url="downloadUrl" export-command-url="exportCommandUrl" />';
    const element = $compile(template)($rootScope);
    $rootScope.$apply();

    return element;
  };

  it('shows TAR.GZ as default option on Mac', () => {
    $window.navigator.appVersion = 'Mac';

    const element = renderTestTemplate();
    expect(element.find('button').text()).toContain('Generate TAR.GZ');
    expect(element.find('ul.dropdown-menu li').text()).toContain(
        'Generate ZIP');
  });

  it('shows ZIP as default option on Linux', () => {
    $window.navigator.appVersion = 'Linux';

    const element = renderTestTemplate();
    expect(element.find('button').text()).toContain('Generate ZIP');
    expect(element.find('ul.dropdown-menu li').text()).toContain(
        'Generate TAR.GZ');
  });

  it('sends TAR.GZ generation request when button clicked on Mac', () => {
    $window.navigator.appVersion = 'Mac';

    const deferred = $q.defer();
    spyOn(grrApiService, 'downloadFile').and.returnValue(deferred.promise);

    const element = renderTestTemplate();
    element.find('button').click();

    expect(grrApiService.downloadFile).toHaveBeenCalledWith(
        'some/download/url', {archive_format: 'TAR_GZ'});
  });

  it('sends ZIP generation request when dropdownclicked on Mac', () => {
    $window.navigator.appVersion = 'Mac';

    const deferred = $q.defer();
    spyOn(grrApiService, 'downloadFile').and.returnValue(deferred.promise);

    const element = renderTestTemplate();
    element.find('ul.dropdown-menu li a').click();

    expect(grrApiService.downloadFile).toHaveBeenCalledWith(
        'some/download/url', {archive_format: 'ZIP'});
  });

  it('sends ZIP generation request when button is clicked on Linux', () => {
    $window.navigator.appVersion = 'Linux';

    const deferred = $q.defer();
    spyOn(grrApiService, 'downloadFile').and.returnValue(deferred.promise);

    const element = renderTestTemplate();
    element.find('button').click();

    expect(grrApiService.downloadFile).toHaveBeenCalledWith(
        'some/download/url', {archive_format: 'ZIP'});
  });

  it('sends TAR.GZ generation request when dropdown clicked on Linux', () => {
    $window.navigator.appVersion = 'Linux';

    const deferred = $q.defer();
    spyOn(grrApiService, 'downloadFile').and.returnValue(deferred.promise);

    const element = renderTestTemplate();
    element.find('ul.dropdown-menu li a').click();

    expect(grrApiService.downloadFile).toHaveBeenCalledWith(
        'some/download/url', {archive_format: 'TAR_GZ'});
  });

  it('disables the button after request is sent', () => {
    const deferred = $q.defer();
    spyOn(grrApiService, 'downloadFile').and.returnValue(deferred.promise);

    const element = renderTestTemplate();
    expect(element.find('button[disabled]').length).toBe(0);

    element.find('ul.dropdown-menu li a').click();

    expect(element.find('button[disabled]').length).not.toBe(0);
  });

  it('shows success message if request succeeds', () => {
    const deferred = $q.defer();
    spyOn(grrApiService, 'downloadFile').and.returnValue(deferred.promise);

    const element = renderTestTemplate();
    element.find('button').click();

    deferred.resolve({status: 'OK'});
    $rootScope.$apply();

    expect(element.text()).toContain('Generation has started.');
  });

  it('shows failure message if request fails', () => {
    const deferred = $q.defer();
    spyOn(grrApiService, 'downloadFile').and.returnValue(deferred.promise);

    const element = renderTestTemplate();
    element.find('button').click();

    deferred.reject({data: {message: 'FAIL'}});
    $rootScope.$apply();

    expect(element.text()).toContain('Can\'t generate archive: FAIL');
  });

  describe('with export command url provided', () => {
    let exportCommandDeferred;

    beforeEach(() => {
      $window.navigator.appVersion = 'Mac';

      exportCommandDeferred = $q.defer();
      spyOn(grrApiService, 'get').and.returnValue(
          exportCommandDeferred.promise);
    });

    it('fetches export command', () => {
      renderTestTemplate(true);
      expect(grrApiService.get).toHaveBeenCalledWith('some/export-command/url');
    });

    it('shows "Show export command" link', () => {
      exportCommandDeferred.resolve({
        data: {
          command: 'blah --foo',
        },
      });
      const element = renderTestTemplate(true);
      expect($('a:contains("Show export command")', element).length)
          .toBe(1);
    });

    it('renders export command', () => {
      exportCommandDeferred.resolve({
        data: {
          command: 'blah --foo',
        },
      });
      const element = renderTestTemplate(true);

      expect($('pre:contains("blah --foo")', element).length).toBe(1);
    });
  });
});


exports = {};
