const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');

const script = fs.readFileSync(path.join(__dirname, '..', 'web', 'site.js'), 'utf8');

function element() {
  return {
    attributes: {},
    setAttribute(name, value) { this.attributes[name] = value; },
    removeAttribute(name) { delete this.attributes[name]; },
    addEventListener() {},
  };
}

function render(search) {
  const ids = Object.fromEntries([
    'page-title', 'page-summary', 'print', 'pdf-link', 'zoom', 'close',
    'lang-fr', 'lang-en', 'zoom-image', 'zoom-title',
  ].map(id => [id, element()]));
  const image = element();
  const card = element();
  card.dataset = {
    id: 'coconut-002', nameFr: 'Ariel — Chanteuse exceptionnelle',
    nameEn: 'Ariel — Spectacular Singer',
  };
  card.querySelector = () => image;
  const sheet = element();
  sheet.nextElementSibling = element();
  const main = element();
  const document = {
    documentElement: {}, title: '',
    getElementById: id => ids[id],
    querySelector: selector => selector === 'main' ? main : null,
    querySelectorAll: selector => selector === '.card' ? [card] : [sheet],
  };
  vm.runInNewContext(script, { document, window: { location: { search } }, URLSearchParams });
  return { document, ids, image, card, main };
}

test('English URL selects English text, image, PDF and accessibility labels', () => {
  const { document, ids, image, card } = render('?lang=en');
  assert.equal(document.documentElement.lang, 'en');
  assert.equal(ids['page-title'].textContent, 'Coconut cards in English');
  assert.equal(image.src, 'images/en/coconut-002.jpg');
  assert.equal(image.alt, 'Ariel — Spectacular Singer');
  assert.equal(card.attributes['aria-label'], 'Enlarge Ariel — Spectacular Singer');
  assert.equal(ids['pdf-link'].href, 'planches-a4-en.pdf');
  assert.equal(ids['lang-en'].attributes['aria-current'], 'page');
  assert.equal(ids['lang-fr'].attributes['aria-current'], undefined);
});

test('French is the default, including for an unknown URL value', () => {
  for (const search of ['', '?lang=invalid', '?lang=fr']) {
    const { document, ids, image } = render(search);
    assert.equal(document.documentElement.lang, 'fr');
    assert.equal(image.src, 'images/coconut-002.jpg');
    assert.equal(image.alt, 'Ariel — Chanteuse exceptionnelle');
    assert.equal(ids['pdf-link'].href, 'planches-a4.pdf');
    assert.equal(ids['lang-fr'].attributes['aria-current'], 'page');
  }
});
