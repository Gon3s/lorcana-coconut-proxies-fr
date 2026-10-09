const language = new URLSearchParams(window.location.search).get('lang') === 'en' ? 'en' : 'fr';
const cards = document.querySelectorAll('.card');
const sheets = document.querySelectorAll('.sheet');
const copy = {
  fr: {
    title: 'Cartes Coconut en français',
    summary: `${cards.length} cartes · ${sheets.length} planches A4 · 63 × 88 mm · traductions non officielles`,
    print: 'Imprimer les planches', pdf: 'Télécharger le PDF',
    main: 'Planches Coconut', sheet: 'Planche', of: 'sur', zoom: 'Agrandir',
    enlarged: 'Carte agrandie', close: 'Fermer',
  },
  en: {
    title: 'Coconut cards in English',
    summary: `${cards.length} cards · ${sheets.length} A4 sheets · 63 × 88 mm · unofficial colour editions`,
    print: 'Print sheets', pdf: 'Download PDF',
    main: 'Coconut sheets', sheet: 'Sheet', of: 'of', zoom: 'Enlarge',
    enlarged: 'Enlarged card', close: 'Close',
  },
}[language];

document.documentElement.lang = language;
document.title = copy.title;
document.getElementById('page-title').textContent = copy.title;
document.getElementById('page-summary').textContent = copy.summary;
document.getElementById('print').textContent = copy.print;
const pdfLink = document.getElementById('pdf-link');
pdfLink.textContent = copy.pdf;
pdfLink.href = language === 'en' ? 'planches-a4-en.pdf' : 'planches-a4.pdf';
document.querySelector('main').setAttribute('aria-label', copy.main);
document.getElementById('zoom').setAttribute('aria-label', copy.enlarged);
document.getElementById('close').textContent = copy.close;
for (const locale of ['fr', 'en']) {
  const link = document.getElementById(`lang-${locale}`);
  if (locale === language) link.setAttribute('aria-current', 'page');
  else link.removeAttribute('aria-current');
}
sheets.forEach((sheet, index) => {
  sheet.setAttribute('aria-label', `${copy.sheet} ${index + 1} ${copy.of} ${sheets.length}`);
  sheet.nextElementSibling.textContent = `${copy.sheet} ${index + 1} / ${sheets.length}`;
});

const zoom = document.getElementById('zoom');
const zoomImage = document.getElementById('zoom-image');
cards.forEach(card => {
  const image = card.querySelector('img');
  const name = language === 'en' ? card.dataset.nameEn : card.dataset.nameFr;
  image.src = language === 'en' ? `images/en/${card.dataset.id}.jpg` : `images/${card.dataset.id}.jpg`;
  image.alt = name;
  card.setAttribute('aria-label', `${copy.zoom} ${name}`);
  card.addEventListener('click', () => {
    zoomImage.src = image.src;
    zoomImage.alt = image.alt;
    document.getElementById('zoom-title').textContent = name;
    zoom.showModal();
  });
});
document.getElementById('close').addEventListener('click', () => zoom.close());
zoom.addEventListener('click', event => { if (event.target === zoom) zoom.close(); });
