
import {HttpErrorResponse} from '@angular/common/http';
import {firstValueFrom, Subject} from 'rxjs';

import {initTestEnvironment} from '../../testing';
import {allValuesFrom} from '../reactive';

import {RequestStatusType, trackRequest} from './track_request';

initTestEnvironment();

describe('trackRequest', () => {
  it('emits SENT when request$ is subscribed', async () => {
    const request$ = new Subject<string>();
    const value = await firstValueFrom(trackRequest(request$));
    expect(value).toEqual({status: RequestStatusType.SENT});
  });

  it('emits SUCCESS and data when request emits next value', async () => {
    const request$ = new Subject<string>();
    const values = allValuesFrom(trackRequest(request$));

    request$.next('successvalue');
    request$.complete();

    expect(await values).toEqual([
      {status: RequestStatusType.SENT},
      {status: RequestStatusType.SUCCESS, data: 'successvalue'}
    ]);
  });

  it('emits ERROR and data when request emits error', async () => {
    const request$ = new Subject<string>();
    const values = allValuesFrom(trackRequest(request$));

    request$.error(new HttpErrorResponse({error: 'errorvalue'}));

    expect(await values).toEqual([
      {status: RequestStatusType.SENT},
      {
        status: RequestStatusType.ERROR,
        error: new HttpErrorResponse({error: 'errorvalue'}),
      },
    ]);
  });

  it('does not catch unknown error types', async () => {
    const request$ = new Subject<string>();
    const values = allValuesFrom(trackRequest(request$));

    request$.error('unexpected error type');

    await expectAsync(values).toBeRejectedWith('unexpected error type');
  });
});
