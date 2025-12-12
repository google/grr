import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {TestBed, fakeAsync, waitForAsync} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {User as ApiUser} from '../../../lib/api/api_interfaces';
import {
  newFlowResult,
  newHuntResult,
} from '../../../lib/models/model_test_util';
import {CollectionResult, PayloadType} from '../../../lib/models/result';
import {initTestEnvironment} from '../../../testing';
import {UsersHarness} from './testing/users_harness';
import {Users} from './users';

initTestEnvironment();

async function createComponent(results: readonly CollectionResult[]) {
  const fixture = TestBed.createComponent(Users);
  fixture.componentRef.setInput('collectionResults', results);

  fixture.detectChanges();
  const harness = await TestbedHarnessEnvironment.harnessForFixture(
    fixture,
    UsersHarness,
  );

  return {fixture, harness};
}

describe('Users Component', () => {
  beforeEach(waitForAsync(() => {
    TestBed.configureTestingModule({
      imports: [Users, NoopAnimationsModule],
      teardown: {destroyAfterEach: true},
    }).compileComponents();
  }));

  it('is created', async () => {
    const {harness, fixture} = await createComponent([]);

    expect(harness).toBeDefined();
    expect(fixture.componentInstance).toBeDefined();
  });

  it('shows users details of a single user', fakeAsync(async () => {
    const {harness} = await createComponent([
      newFlowResult({
        payloadType: PayloadType.USER,
        payload: {
          username: 'foo',
          fullName: 'BAR',
          lastLogon: '1234567890',
          homedir: '/home/foo',
          uid: 123,
          gid: 234,
          shell: '/bin/bash',
        } as ApiUser,
      }),
    ]);

    const usersDetails = await harness.usersDetails();
    expect(usersDetails).toHaveSize(1);
    const userDetails = usersDetails[0];
    expect(await userDetails.numTables()).toBe(1);
    const rowTexts = await userDetails.getRowTexts();
    expect(rowTexts[0]).toContain('foo');
    expect(rowTexts[1]).toContain('BAR');
    expect(rowTexts[2]).toContain('1970-01-01 00:20:34 UTC');
    expect(rowTexts[3]).toContain('/home/foo');
    expect(rowTexts[4]).toContain('123');
    expect(rowTexts[5]).toContain('234');
    expect(rowTexts[6]).toContain('/bin/bash');
  }));

  it('shows users details of multiple users', fakeAsync(async () => {
    const {harness} = await createComponent([
      newFlowResult({
        clientId: 'C.1234',
        payloadType: PayloadType.USER,
        payload: {
          username: 'foo',
          fullName: 'Foo',
          lastLogon: '123',
          homedir: '/home/foo',
          uid: 123,
          gid: 234,
          shell: '/bin/bash',
        } as ApiUser,
      }),
      newFlowResult({
        clientId: 'C.1234',
        payloadType: PayloadType.USER,
        payload: {
          username: 'bar',
          fullName: 'Bar',
          lastLogon: '456',
          homedir: '/home/bar',
          uid: 456,
          gid: 567,
          shell: '/bin/zsh',
        } as ApiUser,
      }),
    ]);

    const usersDetails = await harness.usersDetails();
    expect(usersDetails).toHaveSize(1);
    const userDetails = usersDetails[0];
    expect(await userDetails.numTables()).toBe(2);
  }));

  it('shows client id for hunt results', fakeAsync(async () => {
    const {harness} = await createComponent([
      newHuntResult({
        clientId: 'C.1234',
        payloadType: PayloadType.USER,
      }),
      newHuntResult({
        clientId: 'C.2345',
        payloadType: PayloadType.USER,
      }),
    ]);

    const clientIds = await harness.clientId();
    expect(clientIds).toHaveSize(2);
    expect(await clientIds[0].text()).toContain('C.1234');
    expect(await clientIds[1].text()).toContain('C.2345');
  }));

  it('does not show client id for flow results', fakeAsync(async () => {
    const {harness} = await createComponent([
      newFlowResult({
        clientId: 'C.1234',
        payloadType: PayloadType.USER,
      }),
      newFlowResult({
        clientId: 'C.2345',
        payloadType: PayloadType.USER,
      }),
    ]);

    expect(await harness.clientId()).toHaveSize(0);
  }));

  it('shows users details for each client id in separate tables', fakeAsync(async () => {
    const {harness} = await createComponent([
      newHuntResult({
        clientId: 'C.1234',
        payloadType: PayloadType.USER,
      }),
      newHuntResult({
        clientId: 'C.2345',
        payloadType: PayloadType.USER,
      }),
    ]);

    const usersDetails = await harness.usersDetails();
    expect(usersDetails).toHaveSize(2);
    expect(await usersDetails[0].numTables()).toBe(1);
    expect(await usersDetails[1].numTables()).toBe(1);
  }));
});
