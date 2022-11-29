import {ChangeDetectionStrategy, Component, EventEmitter, Input, Output} from '@angular/core';

import {FlowState} from '../../../lib/models/flow';

/** Flow status (e.g. success, error) to indicate to the user. */
export enum Status {
  NONE,
  IN_PROGRESS,
  SUCCESS,
  WARNING,
  ERROR,
}

/** Flow status (e.g. success, error) to indicate to the user. */
export enum ColorScheme {
  DEFAULT,
  FLOW_ARGS,
  ERROR,
}

const STATUS_ICONS: {[key in Status]: string|null} = {
  [Status.NONE]: null,
  [Status.IN_PROGRESS]: null,
  [Status.SUCCESS]: 'check_circle',
  [Status.ERROR]: 'error',
  [Status.WARNING]: 'warning',
};

const STATUS_CLASSES: {[key in Status]: string|null} = {
  [Status.NONE]: '',
  [Status.IN_PROGRESS]: 'in-progress',
  [Status.SUCCESS]: 'success',
  [Status.ERROR]: 'error',
  [Status.WARNING]: 'warning',
};

const COLOR_SCHEME_CLASSES: {[key in ColorScheme]: string|null} = {
  [ColorScheme.DEFAULT]: 'default',
  [ColorScheme.FLOW_ARGS]: 'flow-args-scheme',
  [ColorScheme.ERROR]: 'error-scheme',
};

/** Component that displays an expendable flow result row. */
@Component({
  selector: 'result-accordion',
  templateUrl: './result_accordion.ng.html',
  styleUrls: ['./result_accordion.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ResultAccordion {
  @Input() title?: string|null;

  @Input() description?: string|null;

  @Input() preview?: string|null;

  @Input() status?: Status|null;

  @Input() expandable: boolean|null = true;

  @Input() colorScheme?: ColorScheme|null;

  @Input() isOpen?: boolean = false;

  @Output() readonly firstOpened = new EventEmitter<void>();

  private firstOpen = true;

  readonly IN_PROGRESS = Status.IN_PROGRESS;

  toggle() {
    if (this.isOpen) {
      this.close();
    } else {
      this.open();
    }
  }

  open() {
    if (!this.expandable) {
      return;
    }

    if (this.firstOpen) {
      this.firstOpen = false;
      this.firstOpened.emit();
      this.firstOpened.complete();
    }

    this.isOpen = true;
  }

  close() {
    this.isOpen = false;
  }

  get icon() {
    return STATUS_ICONS[this.status ?? Status.NONE];
  }

  get rowClass() {
    return STATUS_CLASSES[this.status ?? Status.NONE];
  }

  get colorSchemeClass() {
    return COLOR_SCHEME_CLASSES[this.colorScheme ?? ColorScheme.DEFAULT];
  }
}

/** Derives a ResultAccordion Status from a Flow's state. */
export function fromFlowState(state: FlowState): Status {
  switch (state) {
    case FlowState.RUNNING:
      return Status.IN_PROGRESS;
    case FlowState.FINISHED:
      return Status.SUCCESS;
    case FlowState.ERROR:
      return Status.ERROR;
    default:
      return Status.NONE;
  }
}