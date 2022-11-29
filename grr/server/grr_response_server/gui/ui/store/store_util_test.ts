import {Observable, of, Subject} from 'rxjs';

import {HttpApiService} from '../lib/api/http_api_service';
import {mockHttpApiService} from '../lib/api/http_api_service_test_util';
import {latestValueFrom} from '../lib/reactive';
import {compareAlphabeticallyBy} from '../lib/type_utils';
import {initTestEnvironment} from '../testing';

import {ApiCollectionStore, PaginationArgs} from './store_util';

initTestEnvironment();

interface StoreArgs {
  payload: string;
}

interface ApiResult {
  payload: string;
}

class TestStore extends ApiCollectionStore<ApiResult, StoreArgs> {
  constructor() {
    super(mockHttpApiService() as unknown as HttpApiService);
  }

  apiResults$: Observable<ReadonlyArray<ApiResult>> =
      new Subject<ReadonlyArray<ApiResult>>();
  api = jasmine.createSpy('api').and.callFake(() => this.apiResults$);

  protected loadResults(args: StoreArgs, paginationArgs: PaginationArgs):
      Observable<readonly ApiResult[]> {
    return this.api(args, paginationArgs);
  }

  protected compareItems(a: ApiResult, b: ApiResult): number {
    return compareAlphabeticallyBy<ApiResult>(result => result.payload)(a, b);
  }

  protected areItemsEqual(a: ApiResult, b: ApiResult): boolean {
    return a.payload === b.payload;
  }
}

describe('ApiCollectionStore', () => {
  it('calls the API on subscription', async () => {
    const store = new TestStore();
    store.setArgs({payload: 'foo'});
    expect(store.api).not.toHaveBeenCalled();
    store.results$.subscribe();
    expect(store.api).toHaveBeenCalledWith(
        {payload: 'foo'}, {count: store.INITIAL_LOAD_COUNT, offset: 0});
  });

  it('emits results returned from the API', async () => {
    const store = new TestStore();
    store.setArgs({payload: ''});

    store.apiResults$ = of([{payload: 'a'}, {payload: 'b'}]);
    const results = latestValueFrom(store.results$);

    expect(store.api).toHaveBeenCalled();
    expect(results.get()).toEqual([{payload: 'a'}, {payload: 'b'}]);
  });

  it('passes through polling results', async () => {
    const store = new TestStore();
    store.setArgs({payload: ''});

    const resultSource = new Subject<ReadonlyArray<ApiResult>>();
    store.apiResults$ = resultSource;
    const results = latestValueFrom(store.results$);

    expect(store.api).toHaveBeenCalled();

    resultSource.next([{payload: 'a'}, {payload: 'b'}]);
    expect(results.get()).toEqual([{payload: 'a'}, {payload: 'b'}]);

    resultSource.next([{payload: 'a'}, {payload: 'b'}, {payload: 'c'}]);
    expect(results.get()).toEqual([
      {payload: 'a'}, {payload: 'b'}, {payload: 'c'}
    ]);
  });

  it('merges polled results', async () => {
    const store = new TestStore();
    store.setArgs({payload: ''});

    const resultSource = new Subject<ReadonlyArray<ApiResult>>();
    store.apiResults$ = resultSource;
    const results = latestValueFrom(store.results$);

    expect(store.api).toHaveBeenCalled();

    resultSource.next([{payload: 'a'}]);
    expect(results.get()).toEqual([{payload: 'a'}]);

    resultSource.next([{payload: 'b'}, {payload: 'c'}]);
    expect(results.get()).toEqual([
      {payload: 'a'}, {payload: 'b'}, {payload: 'c'}
    ]);
  });

  it('orders polled results', async () => {
    const store = new TestStore();
    store.setArgs({payload: ''});

    const resultSource = new Subject<ReadonlyArray<ApiResult>>();
    store.apiResults$ = resultSource;
    const results = latestValueFrom(store.results$);

    expect(store.api).toHaveBeenCalled();

    resultSource.next([{payload: 'b'}]);
    expect(results.get()).toEqual([{payload: 'b'}]);

    resultSource.next([{payload: 'a'}, {payload: 'c'}]);
    expect(results.get()).toEqual([
      {payload: 'a'}, {payload: 'b'}, {payload: 'c'}
    ]);
  });

  it('loadMore calls api with pagination data', async () => {
    const store = new TestStore();
    const apiResults$ = new Subject<readonly ApiResult[]>();
    store.apiResults$ = apiResults$;

    store.setArgs({payload: ''});
    store.results$.subscribe();

    expect(store.api).toHaveBeenCalledOnceWith(
        {payload: ''}, {count: store.INITIAL_LOAD_COUNT, offset: 0});
    apiResults$.next([]);

    store.loadMore(10);

    expect(store.api).toHaveBeenCalledWith(
        {payload: ''}, {count: 10, offset: 0});
  });

  it('merges all loadMore results', async () => {
    const store = new TestStore();
    store.setArgs({payload: ''});
    const count = store.INITIAL_LOAD_COUNT;

    store.api = jasmine.createSpy('api').and.callFake(
        (args, paginationArgs) => of([{
          payload: `args=${args.payload} offset=${
              paginationArgs.offset} count=${paginationArgs.count}`
        }]));
    const results = latestValueFrom(store.results$);

    expect(store.api).toHaveBeenCalledOnceWith(
        {payload: ''}, {count, offset: 0});

    expect(results.get()).toEqual([{payload: `args= offset=0 count=${count}`}]);

    store.loadMore(10);
    expect(store.api).toHaveBeenCalledWith(
        {payload: ''}, {count: 10, offset: 1});

    expect(results.get()).toEqual([
      {payload: `args= offset=0 count=${count}`},
      {payload: `args= offset=1 count=10`},
    ]);

    store.loadMore(20);
    expect(store.api).toHaveBeenCalledWith(
        {payload: ''}, {count: 20, offset: 2});

    expect(results.get()).toEqual([
      {payload: `args= offset=0 count=${count}`},
      {payload: `args= offset=1 count=10`},
      {payload: `args= offset=2 count=20`},
    ]);
  });
});
