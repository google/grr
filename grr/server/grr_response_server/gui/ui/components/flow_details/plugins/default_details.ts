import {
  ChangeDetectionStrategy,
  Component,
  OnChanges,
  OnInit,
  SimpleChanges,
} from '@angular/core';

import {Plugin} from './plugin';

/** Default component that renders flow results based on FlowDetailsAdapter. */
@Component({
  standalone: false,
  selector: 'default-flow-details',
  templateUrl: './default_details.ng.html',
  styleUrls: ['./default_details.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class DefaultDetails extends Plugin implements OnInit, OnChanges {
  showFallback = false;

  ngOnInit() {}

  ngOnChanges(changes: SimpleChanges): void {}
}
