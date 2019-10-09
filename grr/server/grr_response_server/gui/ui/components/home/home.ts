import {ChangeDetectionStrategy, Component} from '@angular/core';

/** Provides the top-most component for the GRR UI home page. */
@Component({
  templateUrl: './home.ng.html',
  styleUrls: ['./home.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class HomeComponent {
}
