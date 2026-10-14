/* Optional Google Maps / Places (New). Manual address fields always remain usable. */
window.initLabourMaps = async function() {
    try {
        const {
            Map
        } = await google.maps.importLibrary('maps');
        const {
            AdvancedMarkerElement
        } = await google.maps.importLibrary('marker');
        const {
            PlaceAutocompleteElement
        } = await google.maps.importLibrary('places');
        const instances = new WeakMap();
        const showMap = (container, lat, lng) => {
            const el = container.matches?.('[data-location-map]') ? container : container.querySelector('[data-location-map]');
            if (!el || !Number.isFinite(lat) || !Number.isFinite(lng)) return;
            el.hidden = false;
            let instance = instances.get(el);
            const position = {
                lat,
                lng
            };
            if (!instance) {
                const map = new Map(el, {
                    center: position,
                    zoom: 13,
                    mapId: el.dataset.mapId || 'DEMO_MAP_ID',
                    disableDefaultUI: true,
                    zoomControl: true
                });
                const marker = new AdvancedMarkerElement({
                    map,
                    position,
                    title: 'Service location'
                });
                instance = {
                    map,
                    marker
                };
                instances.set(el, instance);
            } else {
                instance.map.setCenter(position);
                instance.marker.position = position;
            }
        };
        window.labourSetMap = showMap;
        document.querySelectorAll('[data-location-map]').forEach(el => {
            if (el.dataset.lat && el.dataset.lng) showMap(el, Number(el.dataset.lat), Number(el.dataset.lng));
            else {
                const form = el.closest('form');
                const lat = form?.querySelector('[name=latitude]')?.value,
                    lng = form?.querySelector('[name=longitude]')?.value;
                if (lat && lng) showMap(form, Number(lat), Number(lng));
            }
        });
        document.querySelectorAll('[data-maps-autocomplete]').forEach(container => {
            const form = container.closest('form'),
                address = form.querySelector('[data-address]');
            if (!address) return;
            const title = document.createElement('label');
            title.textContent = 'Search an address with Google Places (optional)';
            title.className = 'field-help';
            const autocomplete = new PlaceAutocompleteElement();
            autocomplete.setAttribute('aria-label', 'Search service address');
            container.append(title, autocomplete);
            autocomplete.addEventListener('gmp-select', async event => {
                try {
                    const place = event.placePrediction.toPlace();
                    await place.fetchFields({
                        fields: ['formattedAddress', 'location']
                    });
                    address.value = place.formattedAddress || '';
                    if (place.location) {
                        const lat = place.location.lat(),
                            lng = place.location.lng();
                        form.querySelector('[name=latitude]').value = lat.toFixed(6);
                        form.querySelector('[name=longitude]').value = lng.toFixed(6);
                        showMap(form, lat, lng);
                    }
                } catch (error) {
                    console.warn('Places unavailable; manual address input is still available.');
                }
            });
        });
    } catch (error) {
        console.warn('Google Maps unavailable; use the manual address fields.');
    }
};
window.gm_authFailure = () => {
    document.querySelectorAll('[data-location-map]').forEach(el => el.hidden = true);
    console.warn('Google Maps key was not accepted. Manual address input remains available.');
};