import { Component, OnInit, Input } from '@angular/core';
import { Hash } from '@app/lib/api/api_interfaces';

@Component({
  selector: 'hashes',
  templateUrl: './hashes.ng.html',
  styleUrls: ['./hashes.scss']
})
export class Hashes implements OnInit {
  @Input() hash?: Hash;

  constructor() { }

  ngOnInit(): void {
  }

}
