import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {fakeAsync, TestBed, tick, waitForAsync} from '@angular/core/testing';

import {initTestEnvironment} from '../../../../testing';
import {UsersDetailsHarness} from './testing/users_details_harness';
import {UsersDetails} from './users_details';

initTestEnvironment();

async function createComponent() {
  const fixture = TestBed.createComponent(UsersDetails);
  // Set the default value here as the input is required.
  fixture.componentRef.setInput('users', []);
  fixture.detectChanges();
  const harness = await TestbedHarnessEnvironment.harnessForFixture(
    fixture,
    UsersDetailsHarness,
  );
  return {fixture, harness};
}

describe('Users Details Component', () => {
  beforeEach(waitForAsync(() => {
    TestBed.configureTestingModule({
      imports: [UsersDetails],
      teardown: {destroyAfterEach: true},
    }).compileComponents();
  }));

  it('shows `None` if there are no users', async () => {
    const {fixture, harness} = await createComponent();
    fixture.componentRef.setInput('users', []);
    expect(await harness.hasNoneText()).toBeTrue();
    expect(await harness.numTables()).toBe(0);
  });

  it('shows all details of one user', fakeAsync(async () => {
    const {fixture, harness} = await createComponent();
    fixture.componentRef.setInput('users', [
      {
        username: 'testuser',
        fullName: 'Test User',
        lastLogon: new Date('2020-07-01T13:00:00.000Z'),
        homedir: '/home/testuser',
        uid: '54321',
        gid: '12345',
        shell: '/bin/bash',
      },
    ]);
    tick();
    expect(await harness.hasNoneText()).toBeFalse();
    expect(await harness.numTables()).toBe(1);
    expect(await harness.numRows()).toBe(7);
    const rowTexts = await harness.getRowTexts();

    expect(rowTexts[0]).toContain('Username');
    expect(rowTexts[0]).toContain('testuser');

    expect(rowTexts[1]).toContain('Full name');
    expect(rowTexts[1]).toContain('Test User');

    expect(rowTexts[2]).toContain('Last logon');
    expect(rowTexts[2]).toContain('2020-07-01 13:00:00 UTC');

    expect(rowTexts[3]).toContain('Home directory');
    expect(rowTexts[3]).toContain('/home/testuser');

    expect(rowTexts[4]).toContain('UID');
    expect(rowTexts[4]).toContain('54321');

    expect(rowTexts[5]).toContain('GID');
    expect(rowTexts[5]).toContain('12345');

    expect(rowTexts[6]).toContain('Shell');
    expect(rowTexts[6]).toContain('/bin/bash');
  }));

  it('skips empty fields', fakeAsync(async () => {
    const {fixture, harness} = await createComponent();
    fixture.componentRef.setInput('users', [{}]);
    tick();
    expect(await harness.hasNoneText()).toBeFalse();
    expect(await harness.numTables()).toBe(1);
    expect(await harness.numRows()).toBe(0);
  }));

  it('renders multiple users', fakeAsync(async () => {
    const {fixture, harness} = await createComponent();
    fixture.componentRef.setInput('users', [
      {
        username: 'testuser',
        fullName: 'Test User',
        lastLogon: new Date('2020-07-01T13:00:00.000Z'),
        homedir: '/home/testuser',
        uid: '54321',
        gid: '12345',
        shell: '/bin/bash',
      },
      {
        username: 'testuser2',
        fullName: 'Test User 2',
        lastLogon: new Date('2020-07-01T13:00:00.000Z'),
        homedir: '/home/testuser2',
        uid: '654321',
        gid: '23456',
        shell: '/bin/bash2',
      },
    ]);
    tick();
    expect(await harness.hasNoneText()).toBeFalse();
    expect(await harness.numTables()).toBe(2);
    expect(await harness.numRows()).toBe(14);
  }));
});
