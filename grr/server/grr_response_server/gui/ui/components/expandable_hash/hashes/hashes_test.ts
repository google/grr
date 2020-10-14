import { async, ComponentFixture, TestBed } from '@angular/core/testing';
import {initTestEnvironment} from '@app/testing';
import {By} from '@angular/platform-browser';

import { Hashes, HashText } from './hashes';

initTestEnvironment();


fdescribe('Hashes', () => { // TODO: Remove f
  let component: Hashes;
  let fixture: ComponentFixture<Hashes>;

  beforeEach(async(() => {
    TestBed.configureTestingModule({
      declarations: [ Hashes ]
    })
    .compileComponents();
  }));

  beforeEach(() => {
    fixture = TestBed.createComponent(Hashes);
    component = fixture.componentInstance;

    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should display message if no available hashes', () => {
    component.hashes = { };
    fixture.detectChanges();


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
