import {ChangeDetectionStrategy, Component, OnInit, Output} from '@angular/core';
import {ReplaySubject} from 'rxjs';

import {FlowArgumentForm} from './form_interface';

/** Fallback to display when no form is configured for a Flow. */
@Component({
  template: '',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class FallbackFlowArgsForm<T extends {}> extends
    FlowArgumentForm<T> implements OnInit {
  @Output() readonly formValues$ = new ReplaySubject<T>();
  @Output()
  readonly status$ =
      new ReplaySubject<'VALID'|'INVALID'|'PENDING'|'DISABLED'>();

  ngOnInit() {
    this.formValues$.next(this.defaultFlowArgs);
    this.status$.next('VALID');
  }
}
