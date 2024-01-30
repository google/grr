import {fakeAsync, TestBed} from '@angular/core/testing';
import {firstValueFrom} from 'rxjs';
import {filter} from 'rxjs/operators';

import {HttpApiService} from '../lib/api/http_api_service';
import {
  HttpApiServiceMock,
  mockHttpApiService,
} from '../lib/api/http_api_service_test_util';
import {isNonNull} from '../lib/preconditions';
import {initTestEnvironment} from '../testing';

import {ApprovalCardLocalStore} from './approval_card_local_store';

initTestEnvironment();

describe('ApprovalCardLocalStore', () => {
  let httpApiService: HttpApiServiceMock;
  let approvalCardLocalStore: ApprovalCardLocalStore;

  beforeEach(() => {
    httpApiService = mockHttpApiService();

    TestBed.configureTestingModule({
      imports: [],
      providers: [
        ApprovalCardLocalStore,
        {provide: HttpApiService, useFactory: () => httpApiService},
      ],
      teardown: {destroyAfterEach: false},
    }).compileComponents();

    approvalCardLocalStore = TestBed.inject(ApprovalCardLocalStore);
  });

  it('calls suggest approvers api', fakeAsync(() => {
    approvalCardLocalStore.suggestApprovers('fulano');
    expect(httpApiService.suggestApprovers).toHaveBeenCalledWith('fulano');
  }));

  it('emits approverSuggestions$', fakeAsync(async () => {
    approvalCardLocalStore.suggestApprovers('fulano');
    const promise = firstValueFrom(
      approvalCardLocalStore.approverSuggestions$.pipe(filter(isNonNull)),
    );
    httpApiService.mockedObservables.suggestApprovers.next([
      {username: 'cicrano'},
      {username: 'beltrano'},
    ]);
    expect(await promise).toEqual(['cicrano', 'beltrano']);
  }));
});
