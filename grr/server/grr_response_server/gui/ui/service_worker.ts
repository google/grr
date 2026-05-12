import {clientsClaim} from 'workbox-core';
import {precacheAndRoute} from 'workbox-precaching';

declare const self: ServiceWorkerGlobalScope;

clientsClaim();

precacheAndRoute(self.__WB_MANIFEST || []);
