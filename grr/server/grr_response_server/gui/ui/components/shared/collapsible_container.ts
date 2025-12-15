import {CommonModule} from '@angular/common';
import {ChangeDetectionStrategy, Component, model} from '@angular/core';
import {MatButtonModule} from '@angular/material/button';
import {MatIcon} from '@angular/material/icon';

/** State of the collapsible content. */
export enum CollapsibleState {
  COLLAPSED,
  EXPANDED,
}

/** Title of the collapsible content. */
@Component({
  selector: 'collapsible-title',
  template: `<ng-content />`,
})
export class CollapsibleTitle {}

/** Content of the collapsible content. */
@Component({
  selector: 'collapsible-content',
  template: `<ng-content />`,
})
export class CollapsibleContent {}

/** Chip that shows the validity of an Approval. */
@Component({
  selector: 'collapsible-container',
  templateUrl: './collapsible_container.ng.html',
  styleUrls: ['./collapsible_container.scss'],
  imports: [CommonModule, MatButtonModule, MatIcon],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class CollapsibleContainer {
  state = model<CollapsibleState>(CollapsibleState.EXPANDED);

  protected readonly CollapsibleState = CollapsibleState;

  protected toggleState() {
    const state = this.state();
    if (state === CollapsibleState.COLLAPSED) {
      this.state.set(CollapsibleState.EXPANDED);
    } else {
      this.state.set(CollapsibleState.COLLAPSED);
    }
  }
}
