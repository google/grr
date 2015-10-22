'use strict';

goog.require('grrUi.flow.module');
goog.require('grrUi.tests.module');

describe('grr-flow-status-icon directive', function() {
  var $compile, $rootScope;

  beforeEach(module('/static/angular-components/flow/flow-status-icon.html'));
  beforeEach(module(grrUi.flow.module.name));
  beforeEach(module(grrUi.tests.module.name));


  beforeEach(inject(function($injector) {
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
  }));


  var renderTestTemplate = function(state) {
    $rootScope.flow = {
      type: 'ApiFlow',
      value: {
        state: {
          type: 'EnumNamedValue',
          value: state
        }
      }
    };

    var template = '<grr-flow-status-icon flow="flow" />';
    var element = $compile(template)($rootScope);
    $rootScope.$apply();

    return element;
  };

  it('shows an image for 4 possible flow states', function() {
    var states = ['TERMINATED', 'RUNNING', 'ERROR', 'CLIENT_CRASHED'];

    angular.forEach(states, function(state) {
      var element = renderTestTemplate(state);
      expect($('img', element).length).toBe(1);
    });
  });
});
