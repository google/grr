import {Input, Output} from '@angular/core';
import {Observable} from 'rxjs';

/** Form component to configure arguments for a Flow. */
export abstract class FlowArgumentForm<T extends unknown> {
  @Input() defaultFlowArgs!: T;
  @Output() abstract formValues$: Observable<T>;
  @Output()
  abstract status$: Observable<'VALID'|'INVALID'|'PENDING'|'DISABLED'>;
}
