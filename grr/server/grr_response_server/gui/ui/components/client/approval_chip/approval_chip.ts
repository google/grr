import {ChangeDetectionStrategy, Component, Input} from '@angular/core';
import {BehaviorSubject} from 'rxjs';
import {map} from 'rxjs/operators';

import {ClientApproval, ClientApprovalStatus} from '../../../lib/models/client';

const TITLES: {readonly[key in ClientApprovalStatus['type']]: string} = {
  'expired': 'No access',
  'invalid': 'No access',
  'pending': 'Access pending',
  'valid': 'Access granted',
};

/** Chip that shows the validity of a ClientApproval. */
@Component({
  selector: 'app-approval-chip',
  templateUrl: './approval_chip.ng.html',
  styleUrls: ['./approval_chip.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ApprovalChip {
  @Input()
  set approval(approval: ClientApproval|null) {
    this.approval$.next(approval);
  }

  get approval() {
    return this.approval$.getValue();
  }

  private readonly approval$ = new BehaviorSubject<ClientApproval|null>(null);

  readonly status$ =
      this.approval$.pipe(map(approval => approval?.status.type ?? 'invalid'));

  readonly title$ = this.status$.pipe(map(status => TITLES[status]));
}
