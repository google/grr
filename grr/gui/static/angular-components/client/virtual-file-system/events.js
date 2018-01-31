'use strict';

goog.provide('grrUi.client.virtualFileSystem.events');
goog.provide('grrUi.client.virtualFileSystem.events.REFRESH_FILE_EVENT');
goog.provide('grrUi.client.virtualFileSystem.events.REFRESH_FOLDER_EVENT');


goog.scope(function() {

/**
 * "Refresh folder" event name.
 * @const
 */
grrUi.client.virtualFileSystem.events.REFRESH_FOLDER_EVENT =
    'RefreshFolderEvent';

/**
 * "Refresh file" event name.
 * @const
 */
grrUi.client.virtualFileSystem.events.REFRESH_FILE_EVENT = 'RefreshFileEvent';
});  // goog.scope
