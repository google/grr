import {Injectable, inject} from '@angular/core';
import {Observable, ReplaySubject} from 'rxjs';
import {concatMap, debounceTime} from 'rxjs/operators';

import {HttpApiWithTranslationService} from '../../api/http_api_with_translation_service';
import {GlobComponentExplanation} from '../../models/glob_expression';

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
  private readonly apiService = inject(HttpApiWithTranslationService);

  private readonly input$ = new ReplaySubject<ClientGlobExpression>(1);

  readonly explanation$: Observable<readonly GlobComponentExplanation[]> =
    this.input$.pipe(
      debounceTime(500),
      concatMap(({clientId, globExpression}) =>
        this.apiService.explainGlobExpression(clientId, globExpression, {
          exampleCount: 2,
        }),
      ),
    );

  explain(clientId: string, globExpression: string) {
    this.input$.next({clientId, globExpression});
  }
}
