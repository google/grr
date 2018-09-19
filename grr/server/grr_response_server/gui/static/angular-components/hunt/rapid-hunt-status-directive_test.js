goog.module('grrUi.hunt.rapidHuntStatusDirectiveTest');
goog.setTestOnly();

const {huntModule} = goog.require('grrUi.hunt.hunt');
const {isEligible} = goog.require('grrUi.hunt.rapidHuntStatusDirective');
const {testsModule} = goog.require('grrUi.tests');


describe('rapidHuntStatusDirective.isEligible', () => {

  it('considers FileFinder flow with default args eligible', () => {
    expect(
        isEligible(
            'FileFinder',
            {type: 'FileFinderArgs', value: {}}
        )
    ).toBe(true);
  });

  it('considers ClientFileFinder flow with default args eligible', () => {
    expect(
        isEligible(
            'ClientFileFinder',
            {type: 'FileFinderArgs', value: {}}
        )
    ).toBe(true);
  });

  it('considers ListProcesses flow not eligible', () => {
    expect(
        isEligible(
            'ListProcesses',
            {type: 'ListProcessesArgs', value: {}}
        )
    ).toBe(false);
  });

  it('considers FileFinder with a recursive glob non-eligible', () => {
    expect(
        isEligible(
            'ClientFileFinder',
            {
              type: 'FileFinderArgs',
              value: {
                paths: [
                  {
                    type: 'GlobExpression',
                    value: '/foo/**'
                  }
                ]
              }
            }
        )
    ).toBe(false);
  });

  it('considers FileFinder with a single star in a glob eligible', () => {
    expect(
        isEligible(
            'ClientFileFinder',
            {
              type: 'FileFinderArgs',
              value: {
                paths: [
                  {
                    type: 'GlobExpression',
                    value: '/foo/*'
                  }
                ]
              }
            }
        )
    ).toBe(true);
  });

  it('considers FileFinder with two stars in a glob eligible', () => {
    expect(
        isEligible(
            'ClientFileFinder',
            {
              type: 'FileFinderArgs',
              value: {
                paths: [
                  {
                    type: 'GlobExpression',
                    value: '/foo/*/bar/*'
                  }
                ]
              }
            }
        )
    ).toBe(false);
  });

  it('considers FileFinder with DOWNLOAD action non eligible', () => {
    expect(
        isEligible(
            'ClientFileFinder',
            {
              type: 'FileFinderArgs',
              value: {
                action: {
                  type: 'FileFinderAction',
                  value: {
                    action_type: {
                      type: 'EnumNamedValue',
                      value: 'DOWNLOAD'
                    }
                  }
                }
              }
            }
        )
    ).toBe(false);
  });
});

describe('grr-rapid-hunt-status directive', () => {
  let $compile;
  let $q;
  let $rootScope;
  let grrApiService;


  beforeEach(module('/static/angular-components/hunt/rapid-hunt-status.html'));
  beforeEach(module(huntModule.name));
  beforeEach(module(testsModule.name));

  beforeEach(inject(($injector) => {
    $compile = $injector.get('$compile');
    $rootScope = $injector.get('$rootScope');
    $q = $injector.get('$q');
    grrApiService = $injector.get('grrApiService');
  }));

  const setRapidHuntsEnabled = (flag) => {
    const deferred = $q.defer();
    deferred.resolve({
      data: {
        value: {
          value: flag
        }
      }
    });
    spyOn(grrApiService, 'getCached').and.returnValue(deferred.promise);
  };

  const render = (flowName, flowArgs, clientRate) => {
    $rootScope.flowName = flowName;
    $rootScope.flowArgs = flowArgs;
    $rootScope.clientRate = clientRate;

    const template = '<grr-rapid-hunt-status flow-name="flowName" ' +
          'flow-args="flowArgs" client-rate="clientRate" ' +
          'is-eligible="isEligible" />';
    const element = $compile(template)($rootScope);
    $rootScope.$apply();

    return element;
  };

  it('does nothing if rapid hunts are turned off', () => {
    setRapidHuntsEnabled(false);

    const element = render('FileFinder',
                           {type: 'FileFinderArgs', value:{}},
                           0);
    expect(element.text()).not.toContain('eligible');
  });

  it('correctly renders "eligible" note if rapid hunts are on', () => {
    setRapidHuntsEnabled(true);

    const element = render('FileFinder',
                           {type: 'FileFinderArgs', value:{}},
                           0);
    expect(element.text()).toContain('is eligible');
  });

  it('renders "Client rate set to 0" if rapid hunts are on and client rate is 0',
     () => {
       setRapidHuntsEnabled(true);

       const element = render('FileFinder',
                              {type: 'FileFinderArgs', value:{}},
                              0);
       expect(element.text()).toContain('Client rate set to 0');
     });

  it('omits "Client rate set to 0" if rapid hunts are on but client rate not 0',
     () => {
       setRapidHuntsEnabled(true);

       const element = render('FileFinder',
                              {type: 'FileFinderArgs', value:{}},
                              42);
       expect(element.text()).not.toContain('Client rate set to 0');
     });

  it('correctly renders "non eligible" note if rapid hunts are off', () => {
    setRapidHuntsEnabled(true);

    const element = render('ListProcesses',
                           {type: 'ListProcessesArgs', value:{}},
                           0);
    expect(element.text()).toContain('is not eligible');
  });

});
