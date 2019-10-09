import {ChangeDetectionStrategy, Component} from '@angular/core';

/**
 * The root component.
 */
@Component({
  selector: 'app-root',
  templateUrl: './app.ng.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class App {
  title = 'GRR';
}
