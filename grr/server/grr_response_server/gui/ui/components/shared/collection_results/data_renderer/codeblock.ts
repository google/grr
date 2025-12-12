import {CommonModule} from '@angular/common';
import {ChangeDetectionStrategy, Component, input} from '@angular/core';

/**
 * Component displaying the hardware info.
 */
@Component({
  selector: 'codeblock',
  templateUrl: './codeblock.ng.html',
  styleUrls: ['./codeblock.scss'],
  imports: [CommonModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class Codeblock {
  readonly code = input.required<readonly string[]>();
}
