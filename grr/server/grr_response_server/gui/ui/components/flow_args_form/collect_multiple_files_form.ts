import {ChangeDetectionStrategy, Component, OnDestroy, OnInit, Output} from '@angular/core';
import {FormControl, FormGroup} from '@angular/forms';
import {FlowArgumentForm} from '@app/components/flow_args_form/form_interface';
import {ExplainGlobExpressionService} from '@app/lib/service/explain_glob_expression_service/explain_glob_expression_service';
import {Subject} from 'rxjs';
import {map, shareReplay, takeUntil, withLatestFrom} from 'rxjs/operators';

import {CollectMultipleFilesArgs} from '../../lib/api/api_interfaces';
import {ClientPageFacade} from '../../store/client_page_facade';

/** Form that configures a CollectMultipleFiles flow. */
@Component({
  selector: 'collect-multiple-files-form',
  templateUrl: './collect_multiple_files_form.ng.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
  providers: [ExplainGlobExpressionService],
})
export class CollectMultipleFilesForm extends
    FlowArgumentForm<CollectMultipleFilesArgs> implements OnInit, OnDestroy {
  private readonly unsubscribe$ = new Subject<void>();

  readonly form = new FormGroup({
    pathExpression: new FormControl(),
  });

  @Output()
  readonly formValues$ = this.form.valueChanges.pipe(
      map(values => ({
            pathExpressions: [values.pathExpression],
          })),
      shareReplay(1),
  );

  @Output() readonly status$ = this.form.statusChanges.pipe(shareReplay(1));

  readonly explanation$ = this.globExpressionService.explanation$;

  constructor(
      private readonly clientPageFacade: ClientPageFacade,
      private readonly globExpressionService: ExplainGlobExpressionService,
  ) {
    super();
  }

  ngOnInit() {
    this.form.patchValue({
      pathExpression: this.defaultFlowArgs.pathExpressions?.length ?
          this.defaultFlowArgs.pathExpressions[0] :
          '',
    });

    this.formValues$
        .pipe(
            withLatestFrom(this.clientPageFacade.selectedClient$),
            takeUntil(this.unsubscribe$),
            )
        .subscribe(([values, client]) => {
          this.globExpressionService.explain(
              client.clientId, values.pathExpressions[0]);
        });
  }

  ngOnDestroy() {
    this.unsubscribe$.next();
    this.unsubscribe$.complete();
  }
}
