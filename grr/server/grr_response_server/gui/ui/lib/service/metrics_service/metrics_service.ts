import {Injectable} from '@angular/core';

import {
  ApiIncrementCounterMetricArgs,
  FieldValueFieldType,
} from '../../api/api_interfaces';
import {HttpApiService} from '../../api/http_api_service';

/** Counter metrics available for increase. */
export enum CounterMetric {
  UI_REDIRECT = 'ui_redirect',
}

/** Source field for UI_REDIRECT counter metric. */
export enum UiRedirectSource {
  REDIRECT_BUTTON = 'redirect_button',
  REDIRECT_ROUTER = 'redirect_router',
  RESULT_DETAILS_BUTTON = 'results_button',
}

/** Direction field for UI_REDIRECT counter metric. */
export enum UiRedirectDirection {
  NEW_TO_OLD = 'new_to_old',
  OLD_TO_NEW = 'old_to_new',
}

/**
 * Service that increases UI visit counter.
 */
@Injectable()
export class MetricsService {
  constructor(private readonly apiService: HttpApiService) {}

  registerUIRedirect(direction: UiRedirectDirection, source: UiRedirectSource) {
    const args: ApiIncrementCounterMetricArgs = {
      metricName: CounterMetric.UI_REDIRECT,
      fieldValues: [
        {fieldType: FieldValueFieldType.STRING, stringValue: direction},
        {fieldType: FieldValueFieldType.STRING, stringValue: source},
      ],
    };
    this.apiService.increaseCounterMetric(args).subscribe();
  }
}
