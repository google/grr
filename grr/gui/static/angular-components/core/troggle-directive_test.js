'use strict';

goog.module('grrUi.core.troggleDirectiveTest');

const {TroggleDirective, TroggleState} = goog.require('grrUi.core.troggleDirective');
const {coreModule} = goog.require('grrUi.core.core');


describe('Troggle', () => {
  let $compile;
  let $rootScope;

  beforeEach(module(TroggleDirective().templateUrl));
  beforeEach(module(coreModule.name));

  beforeEach(inject(($injector) => {
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
  }));

  const render = (state) => {
    const template = `<grr-troggle ng-model="state" />`;
    const element = $compile(template)($rootScope);
    $rootScope.$apply();

    return element;
  };

  it('correctly renders `VOID` state', () => {
    $rootScope.state = TroggleState.VOID;

    let element = render();
    expect(element.text().trim()).toBe('_');
  });

  it('correctly renders `SET` state', () => {
    $rootScope.state = TroggleState.SET;

    let element = render();
    expect(element.text().trim()).toBe('✓');
  });

  it('correctly renders `UNSET` state', () => {
    $rootScope.state = TroggleState.UNSET;

    let element = render();
    expect(element.text().trim()).toBe('✕');
  });

  it('changes states when clicked', () => {
    $rootScope.state = TroggleState.VOID;
    let element = render();

    element.find(':first-child').click();
    expect(element.text().trim()).toBe('✓');
    expect($rootScope.state).toBe(TroggleState.SET);

    element.find(':first-child').click();
    expect(element.text().trim()).toBe('✕');
    expect($rootScope.state).toBe(TroggleState.UNSET);

    element.find(':first-child').click();
    expect(element.text().trim()).toBe('_');
    expect($rootScope.state).toBe(TroggleState.VOID);
  });
});
