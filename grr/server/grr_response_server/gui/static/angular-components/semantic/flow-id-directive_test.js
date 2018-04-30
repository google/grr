'use strict';

goog.module('grrUi.semantic.flowIdDirectiveTest');

const {clientModule} = goog.require('grrUi.client.client');
const {semanticModule} = goog.require('grrUi.semantic.semantic');
const {testsModule} = goog.require('grrUi.tests');


describe('grr-flow-id directive', () => {
  let $compile;
  let $rootScope;


  beforeEach(module('/static/angular-components/semantic/flow-id.html'));
  beforeEach(module(clientModule.name));
  beforeEach(module(semanticModule.name));
  beforeEach(module(testsModule.name));

  beforeEach(inject(($injector) => {
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
  }));

  const renderTestTemplate = (value, clientId) => {
    $rootScope.value = value;

    let template = '<grr-flow-id value="value"></grr-flow-id>';
    if (clientId) {
      $rootScope.clientId = clientId;
      template = '<grr-client-context client-id="clientId">' +
          template + '</grr-client-context>';
    }
    const element = $compile(template)($rootScope);
    $rootScope.$apply();

    return element;
  };

  const sampleValue = {
    value: 'F:112233',
    type: 'ApiFlowId',
  };

  describe('without client context', () => {
    it('renders flow id as a string', () => {
      const element = renderTestTemplate(sampleValue);
      expect(element.find('span:contains("F:112233")').length).toBe(1);
      expect(element.find('a:contains("F:112233")').length).toBe(0);
    });
  });

  describe('with client context', () => {
    it('renders flow id as a link', () => {
      const element = renderTestTemplate(sampleValue, 'C.1111222233334444');
      expect(element.find('span:contains("F:112233")').length).toBe(0);

      const aRef = element.find('a:contains("F:112233")');
      expect(aRef.length).toBe(1);
      expect(aRef.attr('href')).toBe(
          '#!/clients/C.1111222233334444/flows/F%3A112233');
    });

    it('renders a tooltip with a client id', () => {
      const element = renderTestTemplate(sampleValue, 'C.1111222233334444');
      const aref = element.find('a:contains("F:112233")');
      expect(aref.attr('title')).toBe('Flow F:112233 ran on client C.1111222233334444');
    });
  });
});


exports = {};
