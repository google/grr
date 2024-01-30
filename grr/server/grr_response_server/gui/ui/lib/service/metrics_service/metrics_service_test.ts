import {fakeAsync, TestBed} from '@angular/core/testing';

import {initTestEnvironment} from '../../../testing';
import {FieldValueFieldType} from '../../api/api_interfaces';
import {HttpApiService} from '../../api/http_api_service';
import {
  HttpApiServiceMock,
  mockHttpApiService,
} from '../../api/http_api_service_test_util';

import {
  CounterMetric,
  MetricsService,
  UiRedirectDirection,
  UiRedirectSource,
} from './metrics_service';

initTestEnvironment();

describe('MetricsService', () => {
  let httpApiService: HttpApiServiceMock;
  let metricsService: MetricsService;

  beforeEach(() => {
    httpApiService = mockHttpApiService();

    TestBed.configureTestingModule({
      imports: [],
      providers: [
        MetricsService,
        // Apparently, useValue creates a copy of the object. Using
        // useFactory, to make sure the instance is shared.
        {provide: HttpApiService, useFactory: () => httpApiService},
      ],
      teardown: {destroyAfterEach: false},
    }).compileComponents();

    metricsService = TestBed.inject(MetricsService);
  });

  it('calls http service with correct params', fakeAsync(() => {
    metricsService.registerUIRedirect(
      UiRedirectDirection.NEW_TO_OLD,
      UiRedirectSource.RESULT_DETAILS_BUTTON,
    );

    expect(httpApiService.increaseCounterMetric).toHaveBeenCalledWith({
      metricName: CounterMetric.UI_REDIRECT,
      fieldValues: [
        {
          fieldType: FieldValueFieldType.STRING,
          stringValue: UiRedirectDirection.NEW_TO_OLD,
        },
        {
          fieldType: FieldValueFieldType.STRING,
          stringValue: UiRedirectSource.RESULT_DETAILS_BUTTON,
        },
      ],
    });
  }));
});
