import {ChangeDetectionStrategy, Component, OnInit, Output} from '@angular/core';
import {FormArray, FormControl, FormGroup} from '@angular/forms';
import {FlowArgumentForm} from '@app/components/flow_args_form/form_interface';
import {map, shareReplay} from 'rxjs/operators';

import {CollectMultipleFilesArgs} from '../../lib/api/api_interfaces';
import {ClientPageFacade} from '../../store/client_page_facade';

/** Form that configures a CollectMultipleFiles flow. */
@Component({
  selector: 'collect-multiple-files-form',
  templateUrl: './collect_multiple_files_form.ng.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class CollectMultipleFilesForm extends
    FlowArgumentForm<CollectMultipleFilesArgs> implements OnInit {
  readonly form = new FormGroup({
    pathExpressions: new FormArray([]),
  });

  @Output()
  readonly formValues$ = this.form.valueChanges.pipe(
      shareReplay(1),
  );

  @Output() readonly status$ = this.form.statusChanges.pipe(shareReplay(1));

  readonly clientId$ = this.clientPageFacade.selectedClient$.pipe(
      map(client => client?.clientId),
  );

  constructor(
      private readonly clientPageFacade: ClientPageFacade,
  ) {
    super();
  }

  ngOnInit() {
    const pathExpressions = this.defaultFlowArgs.pathExpressions?.length ?
        this.defaultFlowArgs.pathExpressions :
        [''];

    pathExpressions.forEach(() => {
      this.addPathExpression();
    });

    this.form.patchValue({pathExpressions});
  }

  get pathExpressions(): FormArray {
    return this.form.get('pathExpressions') as FormArray;
  }

  addPathExpression() {
    this.pathExpressions.push(new FormControl());
  }

  removePathExpression(index: number) {
    this.pathExpressions.removeAt(index);
  }
}
