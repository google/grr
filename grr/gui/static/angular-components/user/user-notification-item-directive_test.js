'use strict';

goog.require('grrUi.user.userNotificationItemDirective.annotateApiNotification');

describe('User notification item directive', function() {

  describe('annotateApiNotification()', function() {
    var annotateApiNotification =
        grrUi.user.userNotificationItemDirective.annotateApiNotification;

    it('returns an annotated notification if a reference is present', function() {
      var notification = {
        value: {
          is_pending: {
            value: true
          },
          message: {
            value: 'Recursive Directory Listing complete 0 nodes, 0 dirs'
          },
          reference: {
            value: {
              type: {
                value: 'VFS'
              },
              vfs: {
                value: {
                  client_id: {
                    value: 'aff4:/C.0000000000000001'
                  },
                  vfs_path: {
                    value: 'aff4:/C.0000000000000001/fs/os'
                  }
                }
              }
            }
          },
          timestamp: {
            value: 1461154705560207
          }
        }
      };
      annotateApiNotification(notification);

      expect(notification.isPending).toBe(true);
      expect(notification.isFileDownload).toBe(false);
      expect(notification.link).toEqual('c=aff4%3A%2FC.0000000000000001' +
          '&aff4_path=aff4%3A%2FC.0000000000000001%2Ffs%2Fos&t=_fs&main=VirtualFileSystemView');
      expect(notification.refType).toEqual('VFS');
    });

    it('handles missing references correctly', function() {
      var notification = {
        value: {
          is_pending: {
            value: false
          },
          message: {
            value: 'Recursive Directory Listing complete 0 nodes, 0 dirs'
          },
          timestamp: {
            value: 1461154705560207
          }
        }
      };
      annotateApiNotification(notification);

      expect(notification.isPending).toBe(false);
      expect(notification.isFileDownload).toBeUndefined();
      expect(notification.link).toBeUndefined();
      expect(notification.refType).toBeUndefined();
    });
  });

});
