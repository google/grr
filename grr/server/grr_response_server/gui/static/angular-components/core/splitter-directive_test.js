goog.module('grrUi.core.splitterDirectiveTest');
goog.setTestOnly();

const {coreModule} = goog.require('grrUi.core.core');
const {testsModule} = goog.require('grrUi.tests');


describe('grr-splitter directive', () => {
  let $compile;
  let $rootScope;
  let $interval;
  const splitSpy = jasmine.createSpy('Split');
  let prevSplit;

  beforeEach(module(coreModule.name));
  beforeEach(module(testsModule.name));

  beforeEach(inject(($injector) => {
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
    $interval = $injector.get('$interval');
  }));

  beforeEach(() => {
    prevSplit = window.Split;
    window.Split = splitSpy;
  });

  afterEach(() => {
    window.Split = prevSplit;
  });

  const renderTestTemplate = (template) => {
    const element = $compile(template)($rootScope);

    // Ensure that grr-splitter element has proper width and height.
    element.css({'width': '300px', height: '300px'});
    // Move the timer forward to make sure grr-splitter sees that its
    // element has a proper size now.
    $interval.flush(101);

    $rootScope.$apply();
    return element;
  };

  it('calls Split() correctly for a simple horizontal splitter', () => {
    const element = renderTestTemplate(`
<div grr-splitter orientation="horizontal">
  <div grr-splitter-pane></div>
  <div grr-splitter-pane></div>
</div>
`);
    expect(splitSpy).toHaveBeenCalled();

    const lastArgs = splitSpy.calls.mostRecent().args;
    expect(lastArgs).toEqual([
      element.find('div[grr-splitter-pane]').toArray(),
      {gutterSize: 4, sizes: [50, 50], direction: 'vertical'},
    ]);
  });

  it('calls Split() correctly for a simple vertical splitter', () => {
    const element = renderTestTemplate(`
<div grr-splitter orientation="vertical">
  <div grr-splitter-pane></div>
  <div grr-splitter-pane></div>
</div>
`);
    expect(splitSpy).toHaveBeenCalled();

    const lastArgs = splitSpy.calls.mostRecent().args;
    expect(lastArgs).toEqual([
      element.find('div[grr-splitter-pane]').toArray(),
      {gutterSize: 4, sizes: [50, 50], direction: 'horizontal'},
    ]);
  });

  it('calls Split() correctly for a vertical splitter with sizes set', () => {
    const element = renderTestTemplate(`
<div grr-splitter orientation="vertical">
  <div grr-splitter-pane size="25"></div>
  <div grr-splitter-pane></div>
</div>
`);
    expect(splitSpy).toHaveBeenCalled();

    const lastArgs = splitSpy.calls.mostRecent().args;
    expect(lastArgs).toEqual([
      element.find('div[grr-splitter-pane]').toArray(),
      {gutterSize: 4, sizes: [25, 75], direction: 'horizontal'},
    ]);
  });

  it('correctly fills-in missing sizes if some are not specified', () => {
  });
});
