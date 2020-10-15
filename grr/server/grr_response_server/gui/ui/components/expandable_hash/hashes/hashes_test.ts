import { async, ComponentFixture, TestBed } from '@angular/core/testing';
import {initTestEnvironment} from '@app/testing';
import {By} from '@angular/platform-browser';

import { Hashes, HashTextAggregator } from './hashes';
import { Hash } from '@app/lib/api/api_interfaces';
import { Component, DebugElement } from '@angular/core';

import { ClipboardModule } from '@angular/cdk/clipboard';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';

initTestEnvironment();

describe('Hashes component', () => {
  beforeEach(async(() => {
    TestBed.configureTestingModule({
      declarations: [
        Hashes,
      ],
      imports: [
        ClipboardModule,
        MatIconModule,
        MatButtonModule,
      ]
    })
    .compileComponents();
  }));

  function createComponentFixtureWith(hashes: Hash):
      ComponentFixture<Hashes> {
    const fixture = TestBed.createComponent(Hashes);
    fixture.componentInstance.hashes = hashes;
    fixture.detectChanges();

    return fixture;
  }

  interface SingleHashFields {
    hashType: string,
    value: string
  }

  function unpackHashHolderDiv(hashDiv?: DebugElement): SingleHashFields {
    const hashTypeDiv = hashDiv?.query(By.css('.hashName'));
    const hashType = hashTypeDiv?.nativeElement.innerText;

    const valueDiv = hashDiv?.query(By.css('.hashValue'));
    const value = valueDiv?.nativeElement.innerText;

    return {hashType, value};
  }

  function getDisplayedHashesWith(hashToUse: Hash) {
    const fixture = createComponentFixtureWith(hashToUse);

    const holderDivs = fixture.debugElement.queryAll(By.css('.hashHolder'));

    return holderDivs.map(unpackHashHolderDiv);
  }

  it('should create', () => {
    const noHashes = { };
    const fixture = createComponentFixtureWith(noHashes);
    expect(fixture).toBeTruthy();
  });

  it('should display warning message if no hashes are available', () => {
    const noHashes = { };
    const fixture = createComponentFixtureWith(noHashes);

    const noHashesDiv = fixture.debugElement.query(By.css('.noHashes'));

    expect(noHashesDiv).toBeTruthy();
    expect(noHashesDiv.nativeElement.innerText).toEqual('no available hashes to display');
  })

  it('should display sha256 hash', () => {
    const sha256Only = {
      sha256: 'sha256-0123456789abcdef'
    };

    const expectedHashName = 'sha256:'
    const expectedHashValue = sha256Only.sha256;

    const displayedHashes = getDisplayedHashesWith(sha256Only);

    expect(displayedHashes.length).toEqual(1);
    expect(displayedHashes[0].hashType).toEqual(expectedHashName);
    expect(displayedHashes[0].value).toEqual(expectedHashValue);
  })

  it('should display sha1 hash', () => {
    const sha1Only = {
      sha1: 'sha1-0123456789abcdef'
    };

    const expectedHashName = 'sha1:'
    const expectedHashValue = sha1Only.sha1;

    const displayedHashes = getDisplayedHashesWith(sha1Only);

    expect(displayedHashes.length).toEqual(1);
    expect(displayedHashes[0].hashType).toEqual(expectedHashName);
    expect(displayedHashes[0].value).toEqual(expectedHashValue);
  })

  it('should display md5 hash', () => {
    const md5Only = {
      md5: 'md5-0123456789abcdef'
    };

    const expectedHashName = 'md5:'
    const expectedHashValue = md5Only.md5;

    const displayedHashes = getDisplayedHashesWith(md5Only);

    expect(displayedHashes.length).toEqual(1);
    expect(displayedHashes[0].hashType).toEqual(expectedHashName);
    expect(displayedHashes[0].value).toEqual(expectedHashValue);
  })

  it('should display all sha256, sha1 and md5', () => {
    const allHashes = {
      sha256: 'sha256-0123456789abcdef',
      sha1: 'sha1-0123456789abcdef',
      md5: 'md5-0123456789abcdef',
    };

    const displayedHashes = getDisplayedHashesWith(allHashes);

    expect(displayedHashes.length).toEqual(3);
    expect(displayedHashes[0].hashType).toEqual('sha256:');
    expect(displayedHashes[0].value).toEqual(allHashes.sha256);

    expect(displayedHashes[1].hashType).toEqual('sha1:');
    expect(displayedHashes[1].value).toEqual(allHashes.sha1);

    expect(displayedHashes[2].hashType).toEqual('md5:');
    expect(displayedHashes[2].value).toEqual(allHashes.md5);
  })
});


describe('HashTextAggregator', () => {
  it('should yield an empty string when no hashes are added', () => {
    const hashText = new HashTextAggregator();

    expect(hashText.toString()).toEqual('');
  });

  it('should include the type of the hash', () => {
    const hashText = new HashTextAggregator();
    const hashType = 'md5';
    const expectedBeginning = `${hashType}:`;

    hashText.includeHashOfType('random', hashType);

    expect(hashText.toString().startsWith(expectedBeginning)).toBeTrue();
  })

  it('should add a newline before subsequent hashes', () => {
    const hashText = new HashTextAggregator();
    const expectedString = 'type1: hash1\ntype2: hash2\ntype3: hash3';

    hashText.includeHashOfType('hash1', 'type1');
    hashText.includeHashOfType('hash2', 'type2');
    hashText.includeHashOfType('hash3', 'type3');

    expect(hashText.toString()).toEqual(expectedString);
  })
})
