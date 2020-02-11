import {TestBed} from '@angular/core/testing';
import {ApiClient, ApiClientApproval, ApiFlow} from '@app/lib/api/api_interfaces';
import {HttpApiService} from '@app/lib/api/http_api_service';
import {ClientApproval} from '@app/lib/models/client';
import {Flow} from '@app/lib/models/flow';
import {ClientFacade} from '@app/store/client_facade';
import {GrrStoreModule} from '@app/store/store_module';
import {initTestEnvironment} from '@app/testing';
import {Subject} from 'rxjs';

initTestEnvironment();

describe('ClientFacade', () => {
  let httpApiService: Partial<HttpApiService>;
  let clientFacade: ClientFacade;
  let apiListApprovals$: Subject<ReadonlyArray<ApiClientApproval>>;
  let apiFetchClient$: Subject<ApiClient>;
  let apiListFlowsForClient$: Subject<ReadonlyArray<ApiFlow>>;

  beforeEach(() => {
    apiListApprovals$ = new Subject();
    apiFetchClient$ = new Subject();
    apiListFlowsForClient$ = new Subject();
    httpApiService = {
      listApprovals:
          jasmine.createSpy('listApprovals').and.returnValue(apiListApprovals$),
      fetchClient:
          jasmine.createSpy('fetchClient').and.returnValue(apiFetchClient$),
      listFlowsForClient: jasmine.createSpy('listFlowsForClient')
                              .and.returnValue(apiListFlowsForClient$),
    };

    TestBed.configureTestingModule({
      imports: [
        GrrStoreModule,
      ],
      providers: [
        ClientFacade,
        {provide: HttpApiService, useValue: httpApiService},
      ],
    });

    clientFacade = TestBed.inject(ClientFacade);
  });

  it('calls the API on listClientApprovals', () => {
    clientFacade.listClientApprovals('C.1234');
    expect(httpApiService.listApprovals).toHaveBeenCalledWith('C.1234');
  });

  it('emits the latest pending approval in latestApproval$', (done) => {
    clientFacade.selectClient('C.1234');
    apiFetchClient$.next({
      clientId: 'C.1234',
    });

    clientFacade.listClientApprovals('C.1234');
    apiListApprovals$.next([
      {
        subject: {clientId: 'C.1234'},
        id: '1',
        reason: 'Old reason',
        isValid: false,
        isValidMessage: 'Approval request is expired.',
        approvers: ['me', 'b'],
        notifiedUsers: ['b', 'c'],
      },
      {
        subject: {clientId: 'C.1234'},
        id: '2',
        reason: 'Pending reason',
        isValid: false,
        isValidMessage: 'Need at least 1 more approvers.',
        approvers: ['me'],
        notifiedUsers: ['b', 'c'],
      },
    ]);

    const expected: ClientApproval = {
      status: {type: 'pending', reason: 'Need at least 1 more approvers.'},
      reason: 'Pending reason',
      clientId: 'C.1234',
      approvalId: '2',
      requestedApprovers: ['b', 'c'],
      approvers: [],
    };

    clientFacade.latestApproval$.subscribe(approval => {
      expect(approval).toEqual(expected);
      done();
    });
  });


  it('calls the listFlow API on select()', () => {
    clientFacade.selectClient('C.1234');
    expect(httpApiService.listFlowsForClient).toHaveBeenCalledWith('C.1234');
  });

  it('emits Flows in reverse-chronological order', done => {
    clientFacade.selectClient('C.1234');
    apiListFlowsForClient$.next([
      {
        flowId: '1',
        lastActiveAt: '999000',
        startedAt: '123000',
        creator: 'rick',
        name: 'ListProcesses'
      },
      {
        flowId: '2',
        lastActiveAt: '999000',
        startedAt: '789000',
        creator: 'morty',
        name: 'GetFile'
      },
      {
        flowId: '3',
        lastActiveAt: '999000',
        startedAt: '456000',
        creator: 'morty',
        name: 'KeepAlive'
      },
    ]);

    const expected: Flow[] = [
      {
        flowId: '2',
        lastActiveAt: new Date(999),
        startedAt: new Date(789),
        creator: 'morty',
        name: 'GetFile'
      },
      {
        flowId: '3',
        lastActiveAt: new Date(999),
        startedAt: new Date(456),
        creator: 'morty',
        name: 'KeepAlive'
      },
      {
        flowId: '1',
        lastActiveAt: new Date(999),
        startedAt: new Date(123),
        creator: 'rick',
        name: 'ListProcesses'
      },
    ];

    clientFacade.flows$.subscribe(flows => {
      expect(flows).toEqual(expected);
      done();
    });
  });
});
