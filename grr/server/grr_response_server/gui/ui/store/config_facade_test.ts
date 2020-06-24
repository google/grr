import {TestBed} from '@angular/core/testing';
import {ApiFlowDescriptor} from '@app/lib/api/api_interfaces';
import {HttpApiService} from '@app/lib/api/http_api_service';
import {ConfigFacade} from '@app/store/config_facade';
import {initTestEnvironment} from '@app/testing';
import {ReplaySubject, Subject} from 'rxjs';

initTestEnvironment();

describe('ConfigFacade', () => {
  let httpApiService: Partial<HttpApiService>;
  let configFacade: ConfigFacade;
  let apiListFlowDescriptors$: Subject<ReadonlyArray<ApiFlowDescriptor>>;
  let apiFetchApprovalConfig$: Subject<ReadonlyArray<ApiFlowDescriptor>>;

  beforeEach(() => {
    apiListFlowDescriptors$ = new ReplaySubject(1);
    apiFetchApprovalConfig$ = new ReplaySubject(1);
    httpApiService = {
      listFlowDescriptors: jasmine.createSpy('listFlowDescriptors')
                               .and.returnValue(apiListFlowDescriptors$),
      fetchApprovalConfig: jasmine.createSpy('fetchApprovalConfig')
                               .and.returnValue(apiFetchApprovalConfig$),
    };

    TestBed.configureTestingModule({
      imports: [],
      providers: [
        ConfigFacade,
        {provide: HttpApiService, useFactory: () => httpApiService},
      ],
    });

    configFacade = TestBed.inject(ConfigFacade);
  });

  it('calls the API on subscription to flowDescriptors$', () => {
    configFacade.flowDescriptors$.subscribe();
    expect(httpApiService.listFlowDescriptors).toHaveBeenCalled();
  });

  it('correctly emits the API results in flowDescriptors$', (done) => {
    const expected = new Map([
      [
        'ClientSideFileFinder', {
          name: 'ClientSideFileFinder',
          friendlyName: 'Get a file',
          category: 'Filesystem',
          defaultArgs: {},
        }
      ],
      [
        'KeepAlive', {
          name: 'KeepAlive',
          friendlyName: 'KeepAlive',
          category: 'Misc',
          defaultArgs: {},
        }
      ],
    ]);

    configFacade.flowDescriptors$.subscribe((results) => {
      expect(results).toEqual(expected);
      done();
    });

    apiListFlowDescriptors$.next([
      {
        name: 'ClientSideFileFinder',
        friendlyName: 'Get a file',
        category: 'Filesystem',
        defaultArgs: {'@type': 'test-type'}
      },
      {
        name: 'KeepAlive',
        category: 'Misc',
        defaultArgs: {'@type': 'test-type'}
      },
    ]);
  });
});
