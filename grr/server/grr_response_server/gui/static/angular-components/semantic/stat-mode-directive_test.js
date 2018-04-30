'use strict';

goog.module('grrUi.semantic.statModeDirectiveTest');

const {semanticModule} = goog.require('grrUi.semantic.semantic');
const {testsModule} = goog.require('grrUi.tests');


describe('stat mode directive', () => {
  let $compile;
  let $rootScope;


  beforeEach(module(semanticModule.name));
  beforeEach(module(testsModule.name));

  beforeEach(inject(($injector) => {
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
  }));

  const render = (value) => {
    $rootScope.value = value;

    const template = '<grr-stat-mode value="value" />';
    const element = $compile(template)($rootScope);
    $rootScope.$apply();

    return element;
  };

  it('does not show anything when value is null', () => {
    const element = render(null);
    expect(element.text().trim()).toBe('-');
  });

  it('does not show anything when value is empty', () => {
    const element = render({});
    expect(element.text().trim()).toBe('-');
  });

  it('indicates regular files', () => {
    const element = render({value: 33188});
    expect(element.text().trim()).toBe('-rw-r--r--');
  });

  it('indicates directories', () => {
    const element = render({value: 16832});
    expect(element.text().trim()).toBe('drwx------');
  });

  it('indicates character devices', () => {
    const element = render({value: 8592});
    expect(element.text().trim()).toBe('crw--w----');
  });

  it('indicates symbolic links', () => {
    const element = render({value: 41325});
    expect(element.text().trim()).toBe('lr-xr-xr-x');
  });

  it('indicates block devices', () => {
    const element = render({value: 24960});
    expect(element.text().trim()).toBe('brw-------');
  });

  it('indicates FIFO pipes', () => {
    const element = render({value: 4516});
    expect(element.text().trim()).toBe('prw-r--r--');
  });

  it('indicates sockets', () => {
    const element = render({value: 50668});
    expect(element.text().trim()).toBe('srwxr-sr--');
  });

  it('considers the S_ISUID flag', () => {
    let element = render({value: 35300});
    expect(element.text().trim()).toBe('-rwsr--r--');

    element = render({value: 35236});
    expect(element.text().trim()).toBe('-rwSr--r--');
  });

  it('considers the S_ISGID flag', () => {
    let element = render({value: 36332});
    expect(element.text().trim()).toBe('-rwsr-sr--');

    element = render({value: 36324});
    expect(element.text().trim()).toBe('-rwsr-Sr--');
  });

  it('considers the S_ISVTX flag', () => {
    let element = render({value: 35812});
    expect(element.text().trim()).toBe('-rwsr--r-T');

    element = render({value: 35813});
    expect(element.text().trim()).toBe('-rwsr--r-t');
  });
});


exports = {};
