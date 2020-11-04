import { Component, Input, ChangeDetectorRef } from '@angular/core';
import { Hash } from '../../lib/api/api_interfaces'

const MAX_TIME_MOUSE_IN_FLIGHT_MS = 200;

/**
 * Displays a default text. When the text is hovered, a pop-up appears
 * with all available hashes, together with copy-to-clipboard buttons.
 */
@Component({
  selector: 'expandable-hash',
  templateUrl: './expandable_hash.ng.html',
  styleUrls: ['./expandable_hash.scss']
})
export class ExpandableHash {
  @Input() hashes?: Hash;

  shouldShowPopup = false;

  private mouseInsidePopup = false;
  private mouseInsideTextArea = false;

  private lastTimeout?: number;

  get atLeastOneHashAvailable() {
    return (this.hashes?.sha256 ?? this.hashes?.sha1 ?? this.hashes?.md5) !== undefined;
  }

  constructor(private changeDetectorRef: ChangeDetectorRef) { }

  mouseEnteredTextArea() {
    this.showPopupNow();
    this.mouseInsideTextArea = true;
  }
  mouseLeftTextArea() {
    this.schedulePopupHiding();
    this.mouseInsideTextArea = false;
  }

  mouseEnteredPopup() {
    this.showPopupNow();
    this.mouseInsidePopup = true;
  }
  mouseLeftPopup() {
    this.hidePopupNow(false);
    this.mouseInsidePopup = false;
  }

  private showPopupNow() {
    this.shouldShowPopup = true;
  }

  private schedulePopupHiding() {
    if (this.lastTimeout) {
      window.clearTimeout(this.lastTimeout);
    }

    this.lastTimeout = window.setTimeout(() => {
      if (!this.mouseInsidePopup && !this.mouseInsideTextArea) {
        this.hidePopupNow(true);
      }
    }, MAX_TIME_MOUSE_IN_FLIGHT_MS);
  }

  private hidePopupNow(forceChangeDetection: boolean) {
    this.shouldShowPopup = false;
    if (forceChangeDetection) {
      this.changeDetectorRef.detectChanges();
    }
  }
}
