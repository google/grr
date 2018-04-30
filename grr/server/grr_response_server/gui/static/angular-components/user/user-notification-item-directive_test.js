'use strict';

goog.module('grrUi.user.userNotificationItemDirectiveTest');

const {annotateApiNotification} = goog.require('grrUi.user.userNotificationItemDirective');

describe('User notification item directive', () => {
  describe('annotateApiNotification()', () => {

    const buildNotification =
        ((reference) => ({
           value: {
             is_pending: {
               value: true,
             },
             message: {
               value: 'Recursive Directory Listing complete 0 nodes, 0 dirs',
             },
             reference: reference,
             timestamp: {
               value: 1461154705560207,
             },
           },
         }));

    it('annotates DISCOVERY notification correctly', () => {
      const notification = buildNotification({
        value: {
          type: {
            value: 'DISCOVERY',
          },
          discovery: {
            value: {
              client_id: {
                value: 'aff4:/C.0000000000000001',
              },
            },
          },
        },
      });
      annotateApiNotification(notification);

      expect(notification.link).toEqual('clients/C.0000000000000001');
      expect(notification.refType).toEqual('DISCOVERY');
    });

    it('annotates HUNT notification correctly', () => {
      const notification = buildNotification({
        value: {
          type: {
            value: 'HUNT',
          },
          hunt: {
            value: {
              hunt_urn: {
                value: 'aff4:/hunts/H:123456',
              },
            },
          },
        },
      });
      annotateApiNotification(notification);

      expect(notification.link).toEqual('hunts/H:123456');
      expect(notification.refType).toEqual('HUNT');
    });

    it('annotates CRON notification correctly', () => {
      const notification = buildNotification({
        value: {
          type: {
            value: 'CRON',
          },
          cron: {
            value: {
              cron_job_urn: {
                value: 'aff4:/cron/FooBar',
              },
            },
          },
        },
      });
      annotateApiNotification(notification);

      expect(notification.link).toEqual('crons/FooBar');
      expect(notification.refType).toEqual('CRON');
    });

    it('annotates FLOW notification correctly', () => {
      const notification = buildNotification({
        value: {
          type: {
            value: 'FLOW',
          },
          flow: {
            value: {
              client_id: {
                value: 'aff4:/C.0001000200030004',
              },
              flow_id: {
                value: 'F:123456',
              },
            },
          },
        },
      });
      annotateApiNotification(notification);

      expect(notification.link).toEqual(
          'clients/C.0001000200030004/flows/F:123456');
      expect(notification.refType).toEqual('FLOW');
    });

    it('annotates CLIENT_APPROVAL notification correctly', () => {
      const notification = buildNotification({
        value: {
          type: {
            value: 'CLIENT_APPROVAL',
          },
          client_approval: {
            value: {
              client_id: {
                value: 'aff4:/C.0001000200030004',
              },
              approval_id: {
                value: 'foo-bar',
              },
              username: {
                value: 'test',
              },
            },
          },
        },
      });
      annotateApiNotification(notification);

      expect(notification.link).toEqual(
          'users/test/approvals/client/C.0001000200030004/foo-bar');
      expect(notification.refType).toEqual('CLIENT_APPROVAL');
    });

    it('annotates HUNT_APPROVAL notification correctly', () => {
      const notification = buildNotification({
        value: {
          type: {
            value: 'HUNT_APPROVAL',
          },
          hunt_approval: {
            value: {
              hunt_id: {
                value: 'H:123456',
              },
              approval_id: {
                value: 'foo-bar',
              },
              username: {
                value: 'test',
              },
            },
          },
        },
      });
      annotateApiNotification(notification);

      expect(notification.link).toEqual(
          'users/test/approvals/hunt/H:123456/foo-bar');
      expect(notification.refType).toEqual('HUNT_APPROVAL');
    });

    it('annotates CRON_JOB_APPROVAL notification correctly', () => {
      const notification = buildNotification({
        value: {
          type: {
            value: 'CRON_JOB_APPROVAL',
          },
          cron_job_approval: {
            value: {
              cron_job_id: {
                value: 'FooBar',
              },
              approval_id: {
                value: 'foo-bar',
              },
              username: {
                value: 'test',
              },
            },
          },
        },
      });
      annotateApiNotification(notification);

      expect(notification.link).toEqual(
          'users/test/approvals/cron-job/FooBar/foo-bar');
      expect(notification.refType).toEqual('CRON_JOB_APPROVAL');
    });


    it('annotates UNKNOWN notification correctly', () => {
      const notification = buildNotification({
        value: {
          type: {
            value: 'UNKNOWN',
          },
          unknown: {
            value: {
              source_urn: {
                value: 'aff4:/foo/bar',
              },
              subject_urn: {
                value: 'aff4:/blah/blah',
              },
            },
          },
        },
      });
      annotateApiNotification(notification);

      expect(notification.link).toBe(null);
      expect(notification.refType).toEqual('UNKNOWN');
    });

    it('handles missing references correctly', () => {
      const notification = {
        value: {
          is_pending: {
            value: false,
          },
          message: {
            value: 'Recursive Directory Listing complete 0 nodes, 0 dirs',
          },
          timestamp: {
            value: 1461154705560207,
          },
        },
      };
      annotateApiNotification(notification);

      expect(notification.isPending).toBe(false);
      expect(notification.link).toBeUndefined();
      expect(notification.refType).toBeUndefined();
    });
  });
});


exports = {};
