import { Component, OnInit, Input } from '@angular/core';
import { Hash } from '@app/lib/api/api_interfaces';

@Component({
  selector: 'hashes',
  templateUrl: './hashes.ng.html',
  styleUrls: ['./hashes.scss']
})
export class Hashes implements OnInit {
  @Input() hash?: Hash;

  get completeHashInformation(): string {
    return `sha256: ${this.hash?.sha256}\nsha1: ${this.hash?.sha1}\nmd5: ${this.hash?.md5}`
  }

  constructor() { }

  ngOnInit(): void {
  }

}
