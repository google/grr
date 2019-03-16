var util = require('util')

var TEMPLATE = "angular.module('%s', []).run(['$templateCache', function($templateCache) {\n" +
  "  $templateCache.put('%s',\n    '%s');\n" +
  '}]);\n'

var SINGLE_MODULE_TPL = '(function(module) {\n' +
  'try {\n' +
  "  module = angular.module('%s');\n" +
  '} catch (e) {\n' +
  "  module = angular.module('%s', []);\n" +
  '}\n' +
  "module.run(['$templateCache', function($templateCache) {\n" +
  "  $templateCache.put('%s',\n    '%s');\n" +
  '}]);\n' +
  '})();\n'

var REQUIRE_MODULE_TPL = 'require([\'%s\'], function(angular) {%s});\n'

var ANGULAR2_TPL = 'window.$templateCache = window.$templateCache || {};\n' +
  "window.$templateCache['%s'] = '%s';\n"

var escapeContent = function (content) {
  return content.replace(/\\/g, '\\\\').replace(/'/g, "\\'").replace(/\r?\n/g, "\\n' +\n    '")
}

var createHtml2JsPreprocessor = function (logger, basePath, config) {
  config = typeof config === 'object' ? config : {}

  var log = logger.create('preprocessor.html2js')
  var getModuleName = typeof config.moduleName === 'function' ? config.moduleName : function () {
    return config.moduleName
  }
  var stripPrefix = new RegExp('^' + (config.stripPrefix || ''))
  var prependPrefix = config.prependPrefix || ''
  var stripSufix = new RegExp((config.stripSuffix || config.stripSufix || '') + '$')
  var cacheIdFromPath = config && config.cacheIdFromPath || function (filepath) {
    return prependPrefix + filepath.replace(stripPrefix, '').replace(stripSufix, '')
  }
  var enableRequireJs = config.enableRequireJs
  var requireJsAngularId = config.requireJsAngularId || 'angular'
  var angular = config.angular || 1

  return function (content, file, done) {
    log.debug('Processing "%s".', file.originalPath)

    var originalPath = file.originalPath.replace(basePath + '/', '')
    var htmlPath = cacheIdFromPath(originalPath)
    var moduleName = getModuleName(htmlPath, originalPath)

    if (!/\.js$/.test(file.path)) {
      file.path = file.path + '.js'
    }

    var tpl
    if (angular === 2 || angular === '2') {
      tpl = util.format(ANGULAR2_TPL, htmlPath, escapeContent(content))
    } else {
      if (moduleName) {
        tpl = util.format(SINGLE_MODULE_TPL, moduleName, moduleName, htmlPath, escapeContent(content))
      } else {
        tpl = util.format(TEMPLATE, htmlPath, htmlPath, escapeContent(content))
      }

      if (enableRequireJs) {
        tpl = util.format(REQUIRE_MODULE_TPL, requireJsAngularId, tpl)
      }
    }

    done(tpl)
  }
}

createHtml2JsPreprocessor.$inject = ['logger', 'config.basePath', 'config.ngHtml2JsPreprocessor']

module.exports = createHtml2JsPreprocessor
