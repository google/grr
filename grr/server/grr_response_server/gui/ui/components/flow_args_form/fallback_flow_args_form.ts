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
  private readonly formValuesSubject = new ReplaySubject<T>(1);
  private readonly statusSubject = new ReplaySubject<'VALID'>(1);

  @Output() readonly formValues$ = this.formValuesSubject.asObservable();
  @Output() readonly status$ = this.statusSubject.asObservable();

  ngOnInit() {
    this.formValuesSubject.next(this.defaultFlowArgs);
    this.statusSubject.next('VALID');
  }
}
