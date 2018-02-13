'use strict';

goog.module('grrUi.core.bindKeyDirectiveTest');

const {browserTriggerKeyDown, testsModule} = goog.require('grrUi.tests');
const {coreModule} = goog.require('grrUi.core.core');


describe('bind key directive', () => {
  let $compile;
  let $rootScope;


  beforeEach(module(coreModule.name));
  beforeEach(module(testsModule.name));

  beforeEach(inject(($injector, _$interval_) => {
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
  }));

  const render = (callback, key) => {
    $rootScope.callback = callback;

    const template =
        '<input type="text" grr-bind-key="callback()" key="' + key + '" />';
    const element = $compile(template)($rootScope);
    $rootScope.$apply();

    return element;
  };

  it('calls the specified function on keydown', (done) => {
    const element = render(done, 13);     // ENTER
    browserTriggerKeyDown(element, 13);
  });

  it('calls the specified function only on specified keydown', () => {
    const callback = (() => {
      fail('Callback should not be called');
    });
    const element = render(callback, 13); // ENTER
    browserTriggerKeyDown(element, 15);   // Raise some other key.
  });
});


exports = {};
