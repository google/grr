'use strict';

goog.module('grrUi.routing.aff4UrnToUrlTest');

const {aff4UrnToUrl} = goog.require('grrUi.routing.aff4UrnToUrl');


describe('aff4UrnToUrl()', () => {
  it('doesn\'t convert random string', () => {
    expect(aff4UrnToUrl('aff4:/foo/bar')).toBe(null);
  });

  it('converts non-flow and non-vfs URN in client scope to the client link',
     () => {
       expect(aff4UrnToUrl('aff4:/C.0001000200030004/foo/bar')).toEqual({
         state: 'client',
         params: {clientId: 'C.0001000200030004'},
       });
     });

  it('converts client-scoped fs/os-prefixed URN to VFS link', () => {
    expect(aff4UrnToUrl('aff4:/C.0001000200030004/fs/os/foo/bar')).toEqual({
      state: 'client.vfs',
      params: {clientId: 'C.0001000200030004', path: 'fs/os/foo/bar'},
    });
  });

  it('converts client-scoped flow URN to a flow link', () => {
    expect(aff4UrnToUrl('aff4:/C.0001000200030004/flows/F:123456')).toEqual({
      state: 'client.flows',
      params: {clientId: 'C.0001000200030004', flowId: 'F:123456'},
    });
  });

  it('converts hunt URN to a hunt link', () => {
    expect(aff4UrnToUrl('aff4:/hunts/H:123456')).toEqual({
      state: 'hunts',
      params: {huntId: 'H:123456'},
    });
  });

  it('converts cron job URN to a cron job link', () => {
    expect(aff4UrnToUrl('aff4:/cron/SomeCronJob')).toEqual({
      state: 'crons',
      params: {cronJobId: 'SomeCronJob'},
    });
  });

  it('converts client approval URN to a client approval link', () => {
    expect(aff4UrnToUrl('aff4:/ACL/C.0001000200030004/test/approval_id'))
        .toEqual({
          state: 'clientApproval',
          params: {
            clientId: 'C.0001000200030004',
            username: 'test',
            approvalId: 'approval_id',
          },
        });
  });

  it('converts hunt approval URN to a hunt approval link', () => {
    expect(aff4UrnToUrl('aff4:/ACL/hunts/H:123456/test/approval_id')).toEqual({
      state: 'huntApproval',
      params: {
        huntId: 'H:123456',
        username: 'test',
        approvalId: 'approval_id',
      },
    });
  });

  it('converts cron job approval URN to a cron job approval link', () => {
    expect(aff4UrnToUrl('aff4:/ACL/cron/SomeCronJob/test/approval_id'))
        .toEqual({
          state: 'cronJobApproval',
          params: {
            cronJobId: 'SomeCronJob',
            username: 'test',
            approvalId: 'approval_id',
          },
        });
  });

  it('handles non-URL-friendly characters correctly', () => {
    expect(aff4UrnToUrl('aff4:/C.0001000200030004/fs/os/_f$o/bA%')).toEqual({
      state: 'client.vfs',
      params: {clientId: 'C.0001000200030004', path: 'fs/os/_f$o/bA%'},
    });
  });
});


exports = {};
