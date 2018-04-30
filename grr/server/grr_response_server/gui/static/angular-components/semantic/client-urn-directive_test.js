'use strict';

goog.module('grrUi.semantic.clientUrnDirectiveTest');

const {browserTriggerEvent, testsModule} = goog.require('grrUi.tests');
const {semanticModule} = goog.require('grrUi.semantic.semantic');


describe('client urn directive', () => {
  let $compile;
  let $q;
  let $rootScope;
  let $timeout;
  let grrApiService;


  beforeEach(module('/static/angular-components/semantic/client-urn.html'));
  beforeEach(module('/static/angular-components/semantic/client-urn-modal.html'));
  beforeEach(module(semanticModule.name));
  beforeEach(module(testsModule.name));

  beforeEach(inject(($injector) => {
    $q = $injector.get('$q');
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
    $timeout = $injector.get('$timeout');
    grrApiService = $injector.get('grrApiService');
  }));

  const renderTestTemplate = (value) => {
    $rootScope.value = value;

    const template = '<grr-client-urn value="value" />';
    const element = $compile(template)($rootScope);
    $rootScope.$apply();

    return element;
  };

  it('does not show anything when value is empty', () => {
    const element = renderTestTemplate(null);
    expect(element.text().trim()).toBe('');
  });

  it('shows string value', () => {
    const element = renderTestTemplate('aff4:/C.0000000000000001');
    expect(element.text()).toContain('C.0000000000000001');
  });

  it('shows value with type information', () => {
    const clientUrn = {
      age: 0,
      type: 'ClientURN',
      value: 'aff4:/C.0000000000000001',
    };
    const element = renderTestTemplate(clientUrn);
    expect(element.text()).toContain('C.0000000000000001');
  });

  it('has a proper href', () => {
    const clientUrn = {
      age: 0,
      type: 'ClientURN',
      value: 'aff4:/C.0000000000000001',
    };

    const element = renderTestTemplate(clientUrn);
    expect(element.find('a').attr('href')).toBe(
        '#!/clients/C.0000000000000001/host-info');
  });

  describe('client urn summary modal dialog', () => {
    beforeEach(() => {
      grrApiService.get = ((urn, params) => {
        expect(urn).toBe('clients/C.0000000000000001');

        return $q((resolve, reject) => {
          resolve({
            data: 'This is a summary',
          });
        });
      });
    });

    afterEach(() => {
      // We have to clean document's body to remove modal windows that were not
      // closed.
      $(document.body).html('');
    });

    it('is shown when info button is clicked', () => {
      const element = renderTestTemplate('aff4:/C.0000000000000001');
      browserTriggerEvent($('button', element), 'click');
      expect($(document.body).text()).toContain(
          'Client C.0000000000000001');
    });

    it('is shown when info button is clicked and value has no "aff4" prefix',
       () => {
         const element = renderTestTemplate('C.0000000000000001');
         browserTriggerEvent($('button', element), 'click');
         expect($(document.body).text()).toContain('Client C.0000000000000001');
       });

    it('closed when close button is clicked', () => {
      const element = renderTestTemplate('aff4:/C.0000000000000001');
      browserTriggerEvent($('button', element), 'click');
      expect($(document.body).text()).toContain(
          'Client C.0000000000000001');

      browserTriggerEvent($('button.close'), 'click');
      $timeout.flush();

      expect($(document.body).text()).not.toContain(
          'Client C.0000000000000001');
    });
  });
});


exports = {};
