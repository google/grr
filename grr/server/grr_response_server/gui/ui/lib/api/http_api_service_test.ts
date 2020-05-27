import {HttpClientTestingModule, HttpTestingController} from '@angular/common/http/testing';
import {TestBed} from '@angular/core/testing';
import {initTestEnvironment} from '@app/testing';
import {reduce} from 'rxjs/operators';
import {ApiListFlowResultsResult} from './api_interfaces';
import {FlowResultsParams, FlowResultsWithSourceParams, HttpApiService, URL_PREFIX} from './http_api_service';
import {ApiModule} from './module';



initTestEnvironment();

describe('HttpApiService', () => {
  let httpApiService: HttpApiService;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [
        ApiModule,
        HttpClientTestingModule,
      ],
      providers: [],
    });

    httpApiService = TestBed.inject(HttpApiService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
  });

  describe('batchListResultsForFlow', () => {
    const paramsList: FlowResultsParams[] = [
      {
        flowId: '42',
        offset: 0,
        count: 100,
        withType: 'bar',
      },
      {
        flowId: '43',
        offset: 0,
        count: 100,
        withTag: 'foo',
      },
    ];

    it('sends one request for each query', () => {
      httpApiService.batchListResultsForFlow('C.1234', paramsList).subscribe();

      httpMock.expectOne(`${
          URL_PREFIX}/clients/C.1234/flows/42/results?offset=0&count=100&with_type=bar`);
      httpMock.expectOne(`${
          URL_PREFIX}/clients/C.1234/flows/43/results?offset=0&count=100&with_tag=foo`);
    });

    it('emits one result per each query', (done) => {
      const response1: ApiListFlowResultsResult = {
        items: [
          {payload: {foo: 'bar1'}},
        ],
      };
      const response2: ApiListFlowResultsResult = {
        items: [
          {payload: {foo: 'bar2'}},
          {payload: {foo: 'bar3'}},
        ],
      };

      httpApiService.batchListResultsForFlow('C.1234', paramsList)
          .pipe(
              // Accumulate all emitted values in a single list.
              reduce(
                  (acc, next) => {
                    return [...acc, next];
                  },
                  [] as FlowResultsWithSourceParams[]),
              )
          .subscribe(res => {
            expect(res.length).toBe(2);

            expect(res[0].params.flowId).toBe('42');
            expect(res[0].params.withTag).toBeUndefined();
            expect(res[0].params.withType).toBe('bar');
            expect(res[0].results.length).toBe(1);

            expect(res[1].params.flowId).toBe('43');
            expect(res[1].params.withTag).toBe('foo');
            expect(res[1].params.withType).toBeUndefined();
            expect(res[1].results.length).toBe(2);

            done();
          });

      const req1 = httpMock.expectOne(`${
          URL_PREFIX}/clients/C.1234/flows/42/results?offset=0&count=100&with_type=bar`);
      expect(req1.request.method).toBe('GET');
      req1.flush(response1);

      const req2 = httpMock.expectOne(`${
          URL_PREFIX}/clients/C.1234/flows/43/results?offset=0&count=100&with_tag=foo`);
      expect(req2.request.method).toBe('GET');
      req2.flush(response2);
    });
  });
});
