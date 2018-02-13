'use strict';

goog.module('grrUi.flow.flowStatusIconDirectiveTest');

const {flowModule} = goog.require('grrUi.flow.flow');
const {testsModule} = goog.require('grrUi.tests');


describe('grr-flow-status-icon directive', () => {
  let $compile;
  let $rootScope;


  beforeEach(module('/static/angular-components/flow/flow-status-icon.html'));
  beforeEach(module(flowModule.name));
  beforeEach(module(testsModule.name));


  beforeEach(inject(($injector) => {
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
  }));


  const renderTestTemplate = (state) => {
    $rootScope.flow = {
      type: 'ApiFlow',
      value: {
        state: {
          type: 'EnumNamedValue',
          value: state,
        },
      },
    };

    const template = '<grr-flow-status-icon flow="flow" />';
    const element = $compile(template)($rootScope);
    $rootScope.$apply();

    return element;
  };

  it('shows an image for 4 possible flow states', () => {
    const states = ['TERMINATED', 'RUNNING', 'ERROR', 'CLIENT_CRASHED'];

    angular.forEach(states, (state) => {
      const element = renderTestTemplate(state);
      expect($('img', element).length).toBe(1);
    });
  });
});


exports = {};
