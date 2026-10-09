const zoom = document.getElementById('zoom');
const zoomImage = document.getElementById('zoom-image');
document.querySelectorAll('.card').forEach(card => {
  card.addEventListener('click', () => {
    const image = card.querySelector('img');
    zoomImage.src = image.src;
    zoomImage.alt = image.alt;
    document.getElementById('zoom-title').textContent = card.dataset.name;
    zoom.showModal();
  });
});
document.getElementById('close').addEventListener('click', () => zoom.close());
zoom.addEventListener('click', event => { if (event.target === zoom) zoom.close(); });
