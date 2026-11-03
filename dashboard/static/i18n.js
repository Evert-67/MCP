/* CodePug i18n — Dutch source strings, independently extensible JSON catalogs.
 * To add a language: add locales/<code>.json and list it in LANGUAGES.
 * Never translate untrusted server data using innerHTML.
 */
(() => {
  "use strict";
  const LANGUAGES = Object.freeze({nl:"Nederlands",en:"English"});
  const originals = new WeakMap();
  const originalAttrs = new WeakMap();
  const cache = {nl:{}};
  let current = "nl";

  function detect() {
    let stored;
    try { stored = localStorage.getItem("codepug.language"); } catch (_) {}
    if (stored && Object.hasOwn(LANGUAGES, stored)) return stored;
    const browser = String(navigator.language || "en").split("-")[0].toLowerCase();
    return Object.hasOwn(LANGUAGES, browser) ? browser : "en";
  }
  async function load(code) {
    if (cache[code]) return cache[code];
    const response = await fetch("/static/locales/" + encodeURIComponent(code) + ".json", {cache:"no-cache"});
    if (!response.ok) throw new Error("Language catalog unavailable");
    const obj = await response.json();
    if (!obj || typeof obj !== "object" || Array.isArray(obj)) throw new Error("Invalid language catalog");
    cache[code] = obj;
    return obj;
  }
  function t(source, vars = {}) {
    const translated = (cache[current] || {})[source] || source;
    return String(translated).replace(/\{(\w+)\}/g, (match,key) =>
      Object.hasOwn(vars,key) ? String(vars[key]) : match);
  }
  function translate(root = document.body) {
    if (!root) return;
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    for (let node = walker.nextNode(); node; node = walker.nextNode()) {
      if (node.parentElement?.closest("script,style,textarea,code,pre")) continue;
      if (!originals.has(node)) originals.set(node, node.nodeValue);
      const original = originals.get(node);
      const raw = original.trim();
      if (!raw) continue;
      // Exact string translation: server names, filenames and user notes are untouched.
      node.nodeValue = original.replace(raw, t(raw));
    }
    const elements = [root, ...root.querySelectorAll("*")];
    for (const el of elements) {
      if (!(el instanceof Element)) continue;
      for (const attribute of ["placeholder","title","aria-label"]) {
        if (!el.hasAttribute(attribute)) continue;
        let saved = originalAttrs.get(el);
        if (!saved) { saved = {}; originalAttrs.set(el,saved); }
        if (!(attribute in saved)) saved[attribute] = el.getAttribute(attribute);
        el.setAttribute(attribute,t(saved[attribute]));
      }
    }
  }
  async function setLanguage(code) {
    if (!Object.hasOwn(LANGUAGES,code)) code = "en";
    try { await load(code); } catch (error) {
      console.warn("CodePug: cannot load language, using Dutch:",error);
      code = "nl";
    }
    current = code;
    try { localStorage.setItem("codepug.language",current); } catch (_) {}
    document.documentElement.lang = current;
    const select = document.getElementById("language");
    if (select) select.value = current;
    translate();
    document.dispatchEvent(new CustomEvent("codepug-language-changed", {detail:{language:current}}));
  }
  const api = Object.freeze({t,translate,setLanguage,get language(){return current;},languages:LANGUAGES});
  window.CodePugI18n = api;
  document.addEventListener("DOMContentLoaded", () => {
    const select = document.getElementById("language");
    if (select) select.addEventListener("change",ev=>setLanguage(ev.target.value));
    setLanguage(detect());
  });
})();
