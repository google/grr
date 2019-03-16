/*! @license Firebase v3.7.8
Build: rev-44ec95c
Terms: https://firebase.google.com/terms/ */

/**
 * @fileoverview Firebase server Auth API.
 * Version: 3.7.8
 *
 * Copyright 2017 Google Inc. All Rights Reserved.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 *
 * @externs
 */

/**
 * Creates a new custom token (JWT) that can be sent back to a client to use
 * with signInWithCustomToken.
 *
 * @deprecated Use the
 * {@link
 *   https://firebase.google.com/docs/reference/admin/node/admin.auth.Auth#createCustomToken
 *   createCustomToken()}
 * method in the
 * {@link
 *   https://firebase.google.com/docs/admin/setup
 *   Firebase Admin Node.js SDK}.
 *
 * @param {string} uid The uid to use as the subject
 * @param {Object=} developerClaims Optional additional claims to include
 *     in the payload of the custom token (JWT)
 *
 * @return {string} The custom token (JWT) for the provided payload.
 */
firebase.auth.Auth.prototype.createCustomToken =
    function(uid, developerClaims) {};

/**
 * Verifies a ID token (JWT). Returns a Promise with the tokens claims. Rejects
 * the promise if the token could not be verified.
 *
 * @deprecated Use the
 * {@link
 *   https://firebase.google.com/docs/reference/admin/node/admin.auth.Auth#verifyIdToken
 *   verifyIdToken()}
 * method in the
 * {@link
 *   https://firebase.google.com/docs/admin/setup
 *   Firebase Admin Node.js SDK}.
 *
 * @param {string} idToken The ID token (JWT) to verify
 * @return {!firebase.Promise<Object>} The Promise that will be fulfilled after
 *     a successful verification
 */
firebase.auth.Auth.prototype.verifyIdToken = function(idToken) {};