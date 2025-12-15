import {CommonModule} from '@angular/common';
import {ChangeDetectionStrategy, Component, input} from '@angular/core';
import {MatIconModule} from '@angular/material/icon';

/** Component that displays an error message with an icon. */
@Component({
  selector: 'error-message',
  templateUrl: './error_message.ng.html',
  styleUrls: ['./error_message.scss'],
  imports: [CommonModule, MatIconModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ErrorMessage {
  readonly message = input.required<string>();
}
