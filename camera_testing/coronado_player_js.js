/*
 * ATTENTION: The "eval" devtool has been used (maybe by default in mode: "development").
 * This devtool is neither made for production nor for readable output files.
 * It uses "eval()" calls to create a separate source file in the browser devtools.
 * If you are trying to read the output file, select a different devtool (https://webpack.js.org/configuration/devtool/)
 * or disable the default devtool with "devtool: false".
 * If you are looking for production-ready output files, see mode: "production" (https://webpack.js.org/configuration/mode/).
 */
/******/ (() => { // webpackBootstrap
/******/ 	var __webpack_modules__ = ({

/***/ "./Scripts/lib/base64.js"
/*!*******************************!*\
  !*** ./Scripts/lib/base64.js ***!
  \*******************************/
(module) {

eval("{// Create Base64 Object\nvar Base64 = {\n  _keyStr: \"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=\",\n  encode: function encode(e) {\n    var t = \"\";\n    var n, r, i, s, o, u, a;\n    var f = 0;\n    e = Base64._utf8_encode(e);\n\n    while (f < e.length) {\n      n = e.charCodeAt(f++);\n      r = e.charCodeAt(f++);\n      i = e.charCodeAt(f++);\n      s = n >> 2;\n      o = (n & 3) << 4 | r >> 4;\n      u = (r & 15) << 2 | i >> 6;\n      a = i & 63;\n\n      if (isNaN(r)) {\n        u = a = 64;\n      } else if (isNaN(i)) {\n        a = 64;\n      }\n\n      t = t + this._keyStr.charAt(s) + this._keyStr.charAt(o) + this._keyStr.charAt(u) + this._keyStr.charAt(a);\n    }\n\n    return t;\n  },\n  decode: function decode(e) {\n    var t = \"\";\n    var n, r, i;\n    var s, o, u, a;\n    var f = 0;\n    e = e.replace(/[^A-Za-z0-9+/=]/g, \"\");\n\n    while (f < e.length) {\n      s = this._keyStr.indexOf(e.charAt(f++));\n      o = this._keyStr.indexOf(e.charAt(f++));\n      u = this._keyStr.indexOf(e.charAt(f++));\n      a = this._keyStr.indexOf(e.charAt(f++));\n      n = s << 2 | o >> 4;\n      r = (o & 15) << 4 | u >> 2;\n      i = (u & 3) << 6 | a;\n      t = t + String.fromCharCode(n);\n\n      if (u != 64) {\n        t = t + String.fromCharCode(r);\n      }\n\n      if (a != 64) {\n        t = t + String.fromCharCode(i);\n      }\n    }\n\n    t = Base64._utf8_decode(t);\n    return t;\n  },\n  _utf8_encode: function _utf8_encode(e) {\n    e = e.replace(/rn/g, \"n\");\n    var t = \"\";\n\n    for (var n = 0; n < e.length; n++) {\n      var r = e.charCodeAt(n);\n\n      if (r < 128) {\n        t += String.fromCharCode(r);\n      } else if (r > 127 && r < 2048) {\n        t += String.fromCharCode(r >> 6 | 192);\n        t += String.fromCharCode(r & 63 | 128);\n      } else {\n        t += String.fromCharCode(r >> 12 | 224);\n        t += String.fromCharCode(r >> 6 & 63 | 128);\n        t += String.fromCharCode(r & 63 | 128);\n      }\n    }\n\n    return t;\n  },\n  _utf8_decode: function _utf8_decode(e) {\n    var t = \"\";\n    var n = 0;\n    var r = c1 = c2 = 0;\n\n    while (n < e.length) {\n      r = e.charCodeAt(n);\n\n      if (r < 128) {\n        t += String.fromCharCode(r);\n        n++;\n      } else if (r > 191 && r < 224) {\n        c2 = e.charCodeAt(n + 1);\n        t += String.fromCharCode((r & 31) << 6 | c2 & 63);\n        n += 2;\n      } else {\n        c2 = e.charCodeAt(n + 1);\n        c3 = e.charCodeAt(n + 2);\n        t += String.fromCharCode((r & 15) << 12 | (c2 & 63) << 6 | c3 & 63);\n        n += 3;\n      }\n    }\n\n    return t;\n  }\n};\nmodule.exports = Base64;\n\n//# sourceURL=webpack://coronado-web/./Scripts/lib/base64.js?\n}");

/***/ },

/***/ "./Scripts/pages/live_video_vjs.js"
/*!*****************************************!*\
  !*** ./Scripts/pages/live_video_vjs.js ***!
  \*****************************************/
(__unused_webpack_module, __webpack_exports__, __webpack_require__) {

"use strict";
eval("{__webpack_require__.r(__webpack_exports__);\n/* harmony import */ var _lib_base64__WEBPACK_IMPORTED_MODULE_0__ = __webpack_require__(/*! ../lib/base64 */ \"./Scripts/lib/base64.js\");\n/* harmony import */ var _lib_base64__WEBPACK_IMPORTED_MODULE_0___default = /*#__PURE__*/__webpack_require__.n(_lib_base64__WEBPACK_IMPORTED_MODULE_0__);\n/* harmony import */ var video_js__WEBPACK_IMPORTED_MODULE_1__ = __webpack_require__(/*! video.js */ \"./node_modules/video.js/dist/video.es.js\");\n/* provided dependency */ var $ = __webpack_require__(/*! jquery */ \"./node_modules/jquery/dist/jquery.js\");\n\n\nvar serverUrl = \"\";\n\nfunction parseEmbedded() {\n  var encoded = $(\"input:hidden[name=_su]\").val();\n  var decoded = _lib_base64__WEBPACK_IMPORTED_MODULE_0___default().decode(encoded).split(\"|\");\n  serverUrl = decoded[0];\n}\n\nvar options = {\n  controls: true,\n  autoplay: true,\n  preload: \"auto\",\n  liveui: true,\n  html5: {\n    vhs: {\n      overrideNative: true,\n      parse708captions: true,\n      captionServices: {\n        SERVICE1: {\n          label: \"English\",\n          language: \"en\"\n        },\n        SERVICE2: {\n          label: \"Spanish\",\n          language: \"es\"\n        }\n      }\n    },\n    nativeTextTracks: false\n  }\n}; // console.dir(options);\n\nparseEmbedded();\nvar mediaUrl = serverUrl + \"/playlist.m3u8?DVR\"; // const mediaUrl = \"https://lax-v1.12milesout.com/coronado-test/coronado/playlist.m3u8\";\n\nvar player = (0,video_js__WEBPACK_IMPORTED_MODULE_1__[\"default\"])(document.querySelector(\"#player\"), options);\nplayer.aspectRatio(\"16:9\");\nplayer.src({\n  src: mediaUrl,\n  type: \"application/x-mpegURL\"\n});\n\n//# sourceURL=webpack://coronado-web/./Scripts/pages/live_video_vjs.js?\n}");

/***/ },

/***/ "?34aa"
/*!******************************!*\
  !*** min-document (ignored) ***!
  \******************************/
() {

eval("{/* (ignored) */\n\n//# sourceURL=webpack://coronado-web/min-document_(ignored)?\n}");

/***/ }

/******/ 	});
/************************************************************************/
/******/ 	// The module cache
/******/ 	var __webpack_module_cache__ = {};
/******/ 	
/******/ 	// The require function
/******/ 	function __webpack_require__(moduleId) {
/******/ 		// Check if module is in cache
/******/ 		var cachedModule = __webpack_module_cache__[moduleId];
/******/ 		if (cachedModule !== undefined) {
/******/ 			return cachedModule.exports;
/******/ 		}
/******/ 		// Check if module exists (development only)
/******/ 		if (__webpack_modules__[moduleId] === undefined) {
/******/ 			var e = new Error("Cannot find module '" + moduleId + "'");
/******/ 			e.code = 'MODULE_NOT_FOUND';
/******/ 			throw e;
/******/ 		}
/******/ 		// Create a new module (and put it into the cache)
/******/ 		var module = __webpack_module_cache__[moduleId] = {
/******/ 			id: moduleId,
/******/ 			loaded: false,
/******/ 			exports: {}
/******/ 		};
/******/ 	
/******/ 		// Execute the module function
/******/ 		__webpack_modules__[moduleId].call(module.exports, module, module.exports, __webpack_require__);
/******/ 	
/******/ 		// Flag the module as loaded
/******/ 		module.loaded = true;
/******/ 	
/******/ 		// Return the exports of the module
/******/ 		return module.exports;
/******/ 	}
/******/ 	
/******/ 	// expose the modules object (__webpack_modules__)
/******/ 	__webpack_require__.m = __webpack_modules__;
/******/ 	
/************************************************************************/
/******/ 	/* webpack/runtime/chunk loaded */
/******/ 	(() => {
/******/ 		var deferred = [];
/******/ 		__webpack_require__.O = (result, chunkIds, fn, priority) => {
/******/ 			if(chunkIds) {
/******/ 				priority = priority || 0;
/******/ 				for(var i = deferred.length; i > 0 && deferred[i - 1][2] > priority; i--) deferred[i] = deferred[i - 1];
/******/ 				deferred[i] = [chunkIds, fn, priority];
/******/ 				return;
/******/ 			}
/******/ 			var notFulfilled = Infinity;
/******/ 			for (var i = 0; i < deferred.length; i++) {
/******/ 				var [chunkIds, fn, priority] = deferred[i];
/******/ 				var fulfilled = true;
/******/ 				for (var j = 0; j < chunkIds.length; j++) {
/******/ 					if ((priority & 1 === 0 || notFulfilled >= priority) && Object.keys(__webpack_require__.O).every((key) => (__webpack_require__.O[key](chunkIds[j])))) {
/******/ 						chunkIds.splice(j--, 1);
/******/ 					} else {
/******/ 						fulfilled = false;
/******/ 						if(priority < notFulfilled) notFulfilled = priority;
/******/ 					}
/******/ 				}
/******/ 				if(fulfilled) {
/******/ 					deferred.splice(i--, 1)
/******/ 					var r = fn();
/******/ 					if (r !== undefined) result = r;
/******/ 				}
/******/ 			}
/******/ 			return result;
/******/ 		};
/******/ 	})();
/******/ 	
/******/ 	/* webpack/runtime/compat get default export */
/******/ 	(() => {
/******/ 		// getDefaultExport function for compatibility with non-harmony modules
/******/ 		__webpack_require__.n = (module) => {
/******/ 			var getter = module && module.__esModule ?
/******/ 				() => (module['default']) :
/******/ 				() => (module);
/******/ 			__webpack_require__.d(getter, { a: getter });
/******/ 			return getter;
/******/ 		};
/******/ 	})();
/******/ 	
/******/ 	/* webpack/runtime/define property getters */
/******/ 	(() => {
/******/ 		// define getter functions for harmony exports
/******/ 		__webpack_require__.d = (exports, definition) => {
/******/ 			for(var key in definition) {
/******/ 				if(__webpack_require__.o(definition, key) && !__webpack_require__.o(exports, key)) {
/******/ 					Object.defineProperty(exports, key, { enumerable: true, get: definition[key] });
/******/ 				}
/******/ 			}
/******/ 		};
/******/ 	})();
/******/ 	
/******/ 	/* webpack/runtime/global */
/******/ 	(() => {
/******/ 		__webpack_require__.g = (function() {
/******/ 			if (typeof globalThis === 'object') return globalThis;
/******/ 			try {
/******/ 				return this || new Function('return this')();
/******/ 			} catch (e) {
/******/ 				if (typeof window === 'object') return window;
/******/ 			}
/******/ 		})();
/******/ 	})();
/******/ 	
/******/ 	/* webpack/runtime/hasOwnProperty shorthand */
/******/ 	(() => {
/******/ 		__webpack_require__.o = (obj, prop) => (Object.prototype.hasOwnProperty.call(obj, prop))
/******/ 	})();
/******/ 	
/******/ 	/* webpack/runtime/make namespace object */
/******/ 	(() => {
/******/ 		// define __esModule on exports
/******/ 		__webpack_require__.r = (exports) => {
/******/ 			if(typeof Symbol !== 'undefined' && Symbol.toStringTag) {
/******/ 				Object.defineProperty(exports, Symbol.toStringTag, { value: 'Module' });
/******/ 			}
/******/ 			Object.defineProperty(exports, '__esModule', { value: true });
/******/ 		};
/******/ 	})();
/******/ 	
/******/ 	/* webpack/runtime/node module decorator */
/******/ 	(() => {
/******/ 		__webpack_require__.nmd = (module) => {
/******/ 			module.paths = [];
/******/ 			if (!module.children) module.children = [];
/******/ 			return module;
/******/ 		};
/******/ 	})();
/******/ 	
/******/ 	/* webpack/runtime/jsonp chunk loading */
/******/ 	(() => {
/******/ 		// no baseURI
/******/ 		
/******/ 		// object to store loaded and loading chunks
/******/ 		// undefined = chunk not loaded, null = chunk preloaded/prefetched
/******/ 		// [resolve, reject, Promise] = chunk loading, 0 = chunk loaded
/******/ 		var installedChunks = {
/******/ 			"pages_live_video": 0
/******/ 		};
/******/ 		
/******/ 		// no chunk on demand loading
/******/ 		
/******/ 		// no prefetching
/******/ 		
/******/ 		// no preloaded
/******/ 		
/******/ 		// no HMR
/******/ 		
/******/ 		// no HMR manifest
/******/ 		
/******/ 		__webpack_require__.O.j = (chunkId) => (installedChunks[chunkId] === 0);
/******/ 		
/******/ 		// install a JSONP callback for chunk loading
/******/ 		var webpackJsonpCallback = (parentChunkLoadingFunction, data) => {
/******/ 			var [chunkIds, moreModules, runtime] = data;
/******/ 			// add "moreModules" to the modules object,
/******/ 			// then flag all "chunkIds" as loaded and fire callback
/******/ 			var moduleId, chunkId, i = 0;
/******/ 			if(chunkIds.some((id) => (installedChunks[id] !== 0))) {
/******/ 				for(moduleId in moreModules) {
/******/ 					if(__webpack_require__.o(moreModules, moduleId)) {
/******/ 						__webpack_require__.m[moduleId] = moreModules[moduleId];
/******/ 					}
/******/ 				}
/******/ 				if(runtime) var result = runtime(__webpack_require__);
/******/ 			}
/******/ 			if(parentChunkLoadingFunction) parentChunkLoadingFunction(data);
/******/ 			for(;i < chunkIds.length; i++) {
/******/ 				chunkId = chunkIds[i];
/******/ 				if(__webpack_require__.o(installedChunks, chunkId) && installedChunks[chunkId]) {
/******/ 					installedChunks[chunkId][0]();
/******/ 				}
/******/ 				installedChunks[chunkId] = 0;
/******/ 			}
/******/ 			return __webpack_require__.O(result);
/******/ 		}
/******/ 		
/******/ 		var chunkLoadingGlobal = self["webpackChunkcoronado_web"] = self["webpackChunkcoronado_web"] || [];
/******/ 		chunkLoadingGlobal.forEach(webpackJsonpCallback.bind(null, 0));
/******/ 		chunkLoadingGlobal.push = webpackJsonpCallback.bind(null, chunkLoadingGlobal.push.bind(chunkLoadingGlobal));
/******/ 	})();
/******/ 	
/************************************************************************/
/******/ 	
/******/ 	// startup
/******/ 	// Load entry module and return exports
/******/ 	// This entry module depends on other loaded chunks and execution need to be delayed
/******/ 	var __webpack_exports__ = __webpack_require__.O(undefined, ["vendor"], () => (__webpack_require__("./Scripts/pages/live_video_vjs.js")))
/******/ 	__webpack_exports__ = __webpack_require__.O(__webpack_exports__);
/******/ 	
/******/ })()
;