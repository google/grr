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
});
