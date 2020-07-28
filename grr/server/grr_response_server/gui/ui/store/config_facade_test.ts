import {TestBed} from '@angular/core/testing';
<<<<<<< HEAD
import {ApiFlowDescriptor, ApiUiConfig} from '@app/lib/api/api_interfaces';
=======
import {ApiClientLabel, ApiFlowDescriptor} from '@app/lib/api/api_interfaces';
>>>>>>> ca5746b6 (Add label to client (#806))
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
<<<<<<< HEAD
  let apiFetchUiConfig$: Subject<ApiUiConfig>;

  beforeEach(() => {
    apiListFlowDescriptors$ = new ReplaySubject(1);
    apiFetchApprovalConfig$ = new Subject();
    apiFetchUiConfig$ = new Subject();
=======
  let apiFetchAllClientsLabels$: Subject<ReadonlyArray<ApiClientLabel>>;

  beforeEach(() => {
    apiListFlowDescriptors$ = new ReplaySubject(1);
    apiFetchApprovalConfig$ = new ReplaySubject(1);
    apiFetchAllClientsLabels$ = new ReplaySubject(1);

>>>>>>> ca5746b6 (Add label to client (#806))
    httpApiService = {
      listFlowDescriptors: jasmine.createSpy('listFlowDescriptors')
                               .and.returnValue(apiListFlowDescriptors$),
      fetchApprovalConfig: jasmine.createSpy('fetchApprovalConfig')
                               .and.returnValue(apiFetchApprovalConfig$),
<<<<<<< HEAD
      fetchUiConfig:
          jasmine.createSpy('fetchUiConfig').and.returnValue(apiFetchUiConfig$),
=======
      fetchAllClientsLabels: jasmine.createSpy('fetchAllClientsLabels')
                                 .and.returnValue(apiFetchAllClientsLabels$),
>>>>>>> ca5746b6 (Add label to client (#806))
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

<<<<<<< HEAD
  it('calls the API on subscription to uiConfig$', () => {
    expect(httpApiService.fetchUiConfig).not.toHaveBeenCalled();
    configFacade.uiConfig$.subscribe();
    expect(httpApiService.fetchUiConfig).toHaveBeenCalled();
  });

  it('correctly emits the API results in uiConfig$', (done) => {
    const expected: ApiUiConfig = {
      profileImageUrl: 'https://foo',
    };

    configFacade.uiConfig$.subscribe((results) => {
=======
  it('calls the API on subscription to clientsLabels$', () => {
    configFacade.clientsLabels$.subscribe();
    expect(httpApiService.fetchAllClientsLabels).toHaveBeenCalled();
  });

  it('correctly emits the translated API results in clientLabels$', (done) => {
    const expected = [
      'first_label',
      'second_label',
    ];

    configFacade.clientsLabels$.subscribe((results) => {
>>>>>>> ca5746b6 (Add label to client (#806))
      expect(results).toEqual(expected);
      done();
    });

<<<<<<< HEAD
    apiFetchUiConfig$.next({
      profileImageUrl: 'https://foo',
    });
=======
    apiFetchAllClientsLabels$.next([
      {
        owner: 'first_owner',
        name: 'first_label',
      },
      {
        owner: 'second_owner',
        name: 'second_label',
      },
    ]);
>>>>>>> ca5746b6 (Add label to client (#806))
  });
});
