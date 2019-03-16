// Copyright 2017 The Closure Library Authors. All Rights Reserved.
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS-IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

goog.provide('goog.events.EventTypeTest');
goog.setTestOnly('goog.events.EventTypeTest');

goog.require('goog.events.BrowserFeature');
goog.require('goog.events.EventType');
goog.require('goog.events.PointerFallbackEventType');
goog.require('goog.testing.jsunit');
goog.require('goog.userAgent');

function testPointerFallbackEventType() {
  if (goog.events.BrowserFeature.POINTER_EVENTS) {
    // Pointer events are supported; use W3C PointerEvent
    assertEquals(
        goog.events.EventType.POINTERDOWN,
        goog.events.PointerFallbackEventType.POINTERDOWN);
  } else if (goog.events.BrowserFeature.MSPOINTER_EVENTS) {
    // Only IE10 should support MSPointerEvent
    assertTrue(
        goog.userAgent.IE && goog.userAgent.isVersionOrHigher('10') &&
        !goog.userAgent.isVersionOrHigher('11'));
    // W3C PointerEvent not supported; fall back to MSPointerEvent
    assertEquals(
        goog.events.EventType.MSPOINTERDOWN,
        goog.events.PointerFallbackEventType.POINTERDOWN);
  } else {
    // Pointer events not supported; fall back to MouseEvent
    assertEquals(
        goog.events.EventType.MOUSEDOWN,
        goog.events.PointerFallbackEventType.POINTERDOWN);
  }
}
