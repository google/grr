// Copyright (c) 2011 Google, Inc.
//
// Permission is hereby granted, free of charge, to any person obtaining a copy
// of this software and associated documentation files (the "Software"), to deal
// in the Software without restriction, including without limitation the rights
// to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
// copies of the Software, and to permit persons to whom the Software is
// furnished to do so, subject to the following conditions:
//
// The above copyright notice and this permission notice shall be included in
// all copies or substantial portions of the Software.
//
// THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
// IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
// FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
// AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
// LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
// OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
// THE SOFTWARE.

/** 
 * @fileoverview A general purpose object proxy that logs all method calls.
 *
 * @author konigsberg@google.com (Robert Konigsberg)
 */

var Proxy = function(delegate) {
  this.delegate__ = delegate;
  this.calls__ = [];
  this.propertiesToTrack__ = [];

  for (var propname in delegate) {
    var type = typeof(delegate[propname]);

    // Functions are passed through to the delegate, and are logged
    // prior to the call.
    if (type == "function") {
      function makeFunc(name) {
        return function() {
          this.log__(name, arguments);
          return this.delegate__[name].apply(this.delegate__, arguments);
        }
      };
      this[propname] = makeFunc(propname);
    } else if (type == "string" || type == "number") {
      // String and number properties are just passed through to the delegate.
      this.propertiesToTrack__.push(propname);
      function makeSetter(name) {
        return function(x) {
          this.delegate__[name] = x;
        }
      };
      this.__defineSetter__(propname, makeSetter(propname));

      function makeGetter(name) {
        return function() {
          return this.delegate__[name];
        }
      };
      this.__defineGetter__(propname, makeGetter(propname));
    }
  }
};

Proxy.prototype.log__ = function(name, args) {
  var properties = {};
  for (var propIdx in this.propertiesToTrack__) {
    var prop = this.propertiesToTrack__[propIdx];
    properties[prop] = this.delegate__[prop];
  }
  var call = { name : name, args : args, properties: properties };
  this.calls__.push(call);
};

Proxy.reset = function(proxy) {
  proxy.calls__ = [];
}
