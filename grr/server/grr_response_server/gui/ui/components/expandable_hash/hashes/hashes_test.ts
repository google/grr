import { async, ComponentFixture, TestBed } from '@angular/core/testing';
import {initTestEnvironment} from '@app/testing';
import {By} from '@angular/platform-browser';

import { Hashes, HashText } from './hashes';
import { Hash } from '@app/lib/api/api_interfaces';
import { Component, DebugElement } from '@angular/core';

initTestEnvironment();

@Component({
  template: `
<hashes
    [hashes]="hashes">
</hashes>`
})
class HashesWrapperComponent {
  hashes?: Hash;
}

fdescribe('Hashes component', () => { // TODO: Remove f
  beforeEach(async(() => {
    TestBed.configureTestingModule({
      declarations: [
        HashesWrapperComponent,
        Hashes,
      ]
    })
    .compileComponents();
  }));

  function createHashesComponentWith(hashes: Hash):
      ComponentFixture<HashesWrapperComponent> {
    const component = TestBed.createComponent(HashesWrapperComponent);
    component.componentInstance.hashes = hashes;
    component.detectChanges();

    return component;
  }

  interface SingleHashFields {
    name: string,
    value: string
  }

  function unpackHashDiv(hashDiv: DebugElement): SingleHashFields {
    const nameDiv = hashDiv.query(By.css('.hashName'));
    const name = nameDiv?.nativeElement.innerText;

    const valueDiv = hashDiv.query(By.css('.hashValue'));
    const value = valueDiv?.nativeElement.innerText;

    return {name, value};
  }

  function testWithSingleHash(hashFields: SingleHashFields) {
    const expectedHashName = hashFields.name + ':';
    const expectedHashValue = hashFields.value;

    const hashToUse: Hash = {
      [hashFields.name]: hashFields.value
    };

    const component = createHashesComponentWith(hashToUse);

    const holderDiv = component.debugElement.query(By.css('.hashHolder'));
    expect(holderDiv).toBeTruthy();

    const hashFieldsToCheck = unpackHashDiv(holderDiv);
    expect(hashFieldsToCheck.name).toEqual(expectedHashName);
    expect(hashFieldsToCheck.value).toEqual(expectedHashValue);
  }

  it('should create', () => {
    const noHashes = { };
    const component = createHashesComponentWith(noHashes);
    expect(component).toBeTruthy();
  });

  it('should display warning message if no hashes are available', () => {
    const noHashes = { };
    const component = createHashesComponentWith(noHashes);

    const noHashesDiv = component.debugElement.query(By.css('.noHashes'));

    expect(noHashesDiv).toBeTruthy();
    expect(noHashesDiv.nativeElement.innerText).toEqual('no available hashes to display');
  })

  it('should display sha256 hash', () => {
    const sha256 = {name: 'sha256', value: '0123456789abcdef'};
    testWithSingleHash(sha256);
  })

  it('should display sha1 hash', () => {
    const sha1 = {name: 'sha1', value: '0123456789abcdef'};
    testWithSingleHash(sha1);
  })

  it('should display md5 hash', () => {
    const md5 = {name: 'md5', value: '0123456789abcdef'};
    testWithSingleHash(md5);
  })
});


describe('HashText', () => {
  it('should yield an empty string when no hashes are added', () => {
    const hashText = new HashText();

    expect(hashText.toString()).toEqual('');
  });

  it('should include the type of the hash', () => {
    const hashText = new HashText();
    const hashType = 'md5';
    const expectedBeginning = `${hashType}:`;

    hashText.includeHashOfType('random', hashType);

    expect(hashText.toString().startsWith(expectedBeginning)).toBeTrue();
  })

  it('should add a newline before subsequent hashes', () => {
    const hashText = new HashText();
    const expectedString = 'type1: hash1\ntype2: hash2\ntype3: hash3';

    hashText.includeHashOfType('hash1', 'type1');
    hashText.includeHashOfType('hash2', 'type2');
    hashText.includeHashOfType('hash3', 'type3');

    expect(hashText.toString()).toEqual(expectedString);
  })
})
