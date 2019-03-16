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
 * @fileoverview Dygraphs options palette.
 *
 * @author konigsberg@google.com (Robert Konigsberg)
 */
"use strict";

/**
 * scope is either "global", "series", "x", "y" or "y2".
 */
function Palette(scope) {
  // Contains pair of "input" (the input object) and "row" (the parent row)
  // Also contains functionString.
  this.model = {};
  // This is meant to be overridden by a palette host.
  this.onchange = function() {};
  this.scope = scope;
  this.root = null;
}

Palette.prototype.create = function(parentElement) {
  var palette = this;

  var table = $("<div>")
      .addClass("palette")
      .width(300)
      .appendTo(parentElement);

  this.root = table;
  this.tooltip = new Tooltip();

  // One row per option.
  $.each(opts, function(opt, optEntry) {
    try {
      var scope = optEntry.scope || [ "global" ]; // Scope can be empty, infer "global" only.
      var valid = scope[0] == "*" || $.inArray(palette.scope, scope) >= 0;
      if (!valid) {
        return;
      }

      var type = optEntry.type;
      var isFunction = type.indexOf("function(") == 0;

      var input;
      if (isFunction) {
        input = $("<button>")
            .click(function(opt, palette) {
               return function(event) {
                 var entry = palette.model[opt];
                 var inputValue = entry.functionString;
                 var type = opts[opt].type;
                 if (inputValue == null || inputValue.length == 0) {
                   inputValue = type + "{\n\n}";
                 }
                 var textarea = new TextArea();
                 textarea.show(opt, inputValue);
                 textarea.okCallback = function(value) {
                   if (value != inputValue) {
                     entry.functionString = value;
                     entry.input.textContent = value ? "defined" : "not defined";
                     palette.onchange();
                   }
                 };
               };
             } (opt, palette) // Instantiating this inner function.
           );
      } else if (type == "boolean") {
        input = $("<button>")
            .click(function(event) {
              var btn = event.target;
              if (btn.value == "none") {
                Palette.populateBooleanButton(btn, "true");
              } else if (btn.value == "true") {
                Palette.populateBooleanButton(btn, "false");
              } else {
                Palette.populateBooleanButton(btn, "none");
              }
              palette.onchange();
            });
      } else {
        input = $("<input>", { type: "text" })
            .addClass("textInput")
            .keypress(function(event) {
              var keycode = event.which;
              if (keycode == 13 || keycode == 8) {
                palette.onchange();
              }
            });
      }

      var row = $("<div>")
          .append($("<span>").addClass("name").text(opt))
          .append($("<span>").addClass("option")
              .append(input));

      row.mouseover(function(source, title, type, body) {
          return function() {
            palette.tooltip.show(source, title, type, body);
          };
        } (row, opt, type, Dygraph.OPTIONS_REFERENCE[opt].description))
        .mouseout(function() { palette.tooltip.hide(); })

      row.appendTo(table);

      palette.model[opt] = { input: input, row: row };
    } catch(err) {
      throw "For option " + opt + ":" + err;
    }
  });

  this.filter("");
}

// TODO: replace semicolon parsing with comma parsing, and supporting quotes.
Palette.parseStringArray = function(value) {
  if (value == null || value.length == 0) {
    return null;
  }
  return value.split(";");
}

Palette.parseBooleanArray = function(value) {
  if (value == null || value.length == 0) {
    return null;
  }
  return value.split(',').map(function(x) {
    return x.trim() == "true";
  });
}

Palette.parseFloatArray = function(value) {
  if (value == null || value.length == 0) {
    return null;
  }
  return value.split(',').map(function(x) {
    return parseFloat(x);
  });
}

Palette.parseIntArray = function(value) {
  if (value == null || value.length == 0) {
    return null;
  }

  return value.split(',').map(function(x) {
    return parseInt(x);
  });
}

Palette.prototype.read = function() {
  var results = {};
  for (var opt in this.model) {
    if (this.model.hasOwnProperty(opt)) {
      var type = opts[opt].type;
      var isFunction = type.indexOf("function(") == 0;
      var input = this.model[opt].input[0]; // jquery dereference.
      var value = isFunction ? this.model[opt].functionString : input.value;
      if (value && value.length != 0) {
        if (type == "boolean") {
          if (value == "false") {
            results[opt] = false;
          }
          if (value == "true") {
            results[opt] = true;
          }
          // Ignore value == "none"
        } else if (type == "int") {
          results[opt] = parseInt(value);
        } else if (type == "float") {
          results[opt] = parseFloat(value);
        } else if (type == "array<string>") {
          results[opt] = Palette.parseStringArray(value);
        } else if (type == "array<float>") {
          results[opt] = Palette.parseFloatArray(value);
        } else if (type == "array<boolean>") {
          results[opt] = Palette.parseBooleanArray(value);
        } else if (type == "array<int>") {
          results[opt] = Palette.parseIntArray(value);
        } else if (type == "array<Date>") {
          results[opt] = Palette.parseIntArray(value);
        } else if (isFunction) {
          var localVariable = null;
          eval("localVariable = " + value);
          results[opt] = localVariable;
        } else {
          results[opt] = value;
        }
      }
    }
  }
  return results;
}

/**
 * Write to input elements.
 */
Palette.prototype.write = function(hash) {
  if (!hash) {
    return;
  }
  var results = {};
  for (var opt in this.model) {
    if (this.model.hasOwnProperty(opt)) {
      var input = this.model[opt].input[0]; // jquery dereference
      var type = opts[opt].type;
      var value = hash[opt];
      if (type == "boolean") {
        var text = value == true ? "true" : (value == false ? "false" : "none");
        Palette.populateBooleanButton(input, text);
      } else if (type == "array<string>") {
        if (value) {
          input.value = value.join("; ");
        }
      } else if (type.indexOf("array") == 0) {
        if (value) {
          input.value = value.join(", ");
        }
      } else if (type.indexOf("function(") == 0) {
        input.textContent = value ? "defined" : "not defined";
        this.model[opt].functionString = value ? value.toString() : null;
      } else {
        if (value != undefined) {
          input.value = value;
        }
      }
    }
  }
}

Palette.populateBooleanButton = function(button, value) {
  button.innerHTML = value;
  button.value = value;
}

Palette.prototype.filter = function(pattern) {
  pattern = pattern.toLowerCase();
  var even = true;
  for (var opt in this.model) {
    if (this.model.hasOwnProperty(opt)) {
      var row = this.model[opt].row;
      var matches = opt.toLowerCase().indexOf(pattern) >= 0;
      row.toggle(matches);
      if (matches) {
        row.attr("class", even ? "even" : "odd");
        even = !even;
      }
    }
  }
}
