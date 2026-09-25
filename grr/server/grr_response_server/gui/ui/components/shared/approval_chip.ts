import {CommonModule} from '@angular/common';
import {
  ChangeDetectionStrategy,
  Component,
  computed,
  input,
} from '@angular/core';
import {MatChipsModule} from '@angular/material/chips';
import {MatIconModule} from '@angular/material/icon';

import {DateTime} from '../../lib/date_time';
import {ApprovalStatus, type Approval} from '../../lib/models/user';

const TITLES: {readonly [key in ApprovalStatus['type']]: string} = {
  'expired': 'No access',
  'invalid': 'No access',
  'pending': 'Access pending',
  'valid': 'Access granted',
};

/** Chip that shows the validity of an Approval. */
@Component({
  selector: 'approval-chip',
  templateUrl: './approval_chip.ng.html',
  imports: [CommonModule, MatChipsModule, MatIconModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ApprovalChip {
  readonly approval = input<Approval | null>();

  readonly status = computed(() => this.approval()?.status.type ?? 'invalid');
  readonly title = computed(() => TITLES[this.status()]);

  readonly timeUntilExpiry = computed((): string => {
    const expirationTime = this.approval()?.expirationTime;
    if (expirationTime) {
      const date = DateTime.fromJSDate(expirationTime);
      return ` –  ${date.toRelative()!.replace('in ', '')} left`;
    } else {
      return '';
    }
  });
}
