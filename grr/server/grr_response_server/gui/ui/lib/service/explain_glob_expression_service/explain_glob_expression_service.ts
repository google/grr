import {Injectable} from '@angular/core';
import {HttpApiService} from '@app/lib/api/http_api_service';
import {Observable, ReplaySubject} from 'rxjs';
import {concatMap, debounceTime} from 'rxjs/operators';

import {GlobComponentExplanation} from '../../api/api_interfaces';

interface ClientGlobExpression {
  clientId: string;
  globExpression: string;
}

/**
 * Service that explains how GlobExpressions will be interpreted in a Client,
 * e.g. by showing examples for %%variable%% substitutions.
 */
@Injectable()
export class ExplainGlobExpressionService {
  private readonly input$ = new ReplaySubject<ClientGlobExpression>(1);

  readonly explanation$: Observable<ReadonlyArray<GlobComponentExplanation>> =
      this.input$.pipe(
          debounceTime(500),
          concatMap(
              ({clientId, globExpression}) =>
                  this.apiService.explainGlobExpression(
                      clientId, globExpression, {exampleCount: 2})),
      );

  constructor(private readonly apiService: HttpApiService) {}

  explain(clientId: string, globExpression: string) {
    this.input$.next({clientId, globExpression});
  }
}
