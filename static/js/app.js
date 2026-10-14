/* Progressive enhancement. All permissions and state changes are validated in Django. */
document.addEventListener('DOMContentLoaded', () => {
    const prefersReduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const toast = (message, type = 'info') => {
        const stack = document.querySelector('.toast-stack');
        const item = document.createElement('div');
        item.className = `app-toast ${type}`;
        const icon = document.createElement('i');
        icon.className = 'bi bi-info-circle';
        const text = document.createElement('span');
        text.textContent = message;
        const close = document.createElement('button');
        close.className = 'toast-dismiss';
        close.textContent = '×';
        close.setAttribute('aria-label', 'Dismiss notification');
        close.onclick = () => item.remove();
        item.setAttribute('role', 'status');
        item.append(icon, text, close);
        stack.append(item);
        setTimeout(() => item.remove(), 10000);
    };
    document.querySelectorAll('.toast-dismiss').forEach(button => button.onclick = () => button.closest('.app-toast').remove());
    document.querySelectorAll('input[type="password"]').forEach(input => {
        const wrap = document.createElement('div');
        wrap.className = 'password-wrap';
        input.parentNode.insertBefore(wrap, input);
        wrap.append(input);
        const button = document.createElement('button');
        button.type = 'button';
        button.className = 'password-toggle';
        button.innerHTML = '<i class="bi bi-eye"></i>';
        button.setAttribute('aria-label', 'Show password');
        button.addEventListener('click', () => {
            const show = input.type === 'password';
            input.type = show ? 'text' : 'password';
            button.setAttribute('aria-label', show ? 'Hide password' : 'Show password');
            button.innerHTML = `<i class="bi bi-eye${show ? '-slash' : ''}"></i>`;
        });
        wrap.append(button);
    });
    const registration = document.querySelector('#registrationForm');
    if (registration) {
        const updateRole = () => {
            const worker = registration.querySelector('input[name=role]:checked')?.value === 'WORKER';
            const fields = document.querySelector('#workerFields');
            fields.hidden = !worker;
            fields.querySelectorAll('input,select,textarea').forEach(input => {
                input.disabled = !worker;
                input.required = worker && input.name !== 'skill_document';
            });
            registration.querySelector('[name=profile_photo]').required = worker;
        };
        registration.querySelectorAll('[name=role]').forEach(input => input.addEventListener('change', updateRole));
        updateRole();
    }
    document.querySelectorAll('[data-geolocate]').forEach(button => button.addEventListener('click', () => {
        const form = button.closest('form');
        const status = form.querySelector('[data-location-message]');
        if (!navigator.geolocation) {
            status.textContent = 'Location is not supported. Please enter your address.';
            return;
        }
        status.textContent = 'Requesting your permission to share location…';
        button.disabled = true;
        navigator.geolocation.getCurrentPosition(position => {
            const lat = position.coords.latitude.toFixed(6),
                lng = position.coords.longitude.toFixed(6);
            const latInput = form.querySelector('[name=latitude]'),
                lngInput = form.querySelector('[name=longitude]');
            if (latInput && lngInput) {
                latInput.value = lat;
                lngInput.value = lng;
            }
            status.textContent = `Location saved (${lat}, ${lng}). Check your written address before submitting.`;
            button.disabled = false;
            if (window.labourSetMap) window.labourSetMap(form, Number(lat), Number(lng));
        }, error => {
            status.textContent = error.code === 1 ? 'Location permission declined. You can type your address.' : 'Could not get your location. Please enter it manually.';
            button.disabled = false;
        }, {
            enableHighAccuracy: false,
            timeout: 10000,
            maximumAge: 60000
        });
    }));
    const sidebar = document.querySelector('.sidebar'),
        overlay = document.querySelector('.sidebar-overlay'),
        sidebarToggle = document.querySelector('.sidebar-toggle');
    if (sidebar && overlay) {
        const setOpen = open => {
            sidebar.classList.toggle('open', open);
            overlay.hidden = !open;
            sidebarToggle?.setAttribute('aria-expanded', String(open));
            document.body.style.overflow = open ? 'hidden' : '';
        };
        sidebarToggle?.addEventListener('click', () => setOpen(!sidebar.classList.contains('open')));
        overlay.addEventListener('click', () => setOpen(false));
        document.addEventListener('keydown', e => {
            if (e.key === 'Escape') setOpen(false);
        });
        sidebar.querySelectorAll('a').forEach(link => link.addEventListener('click', () => setOpen(false)));
    }
    let pendingForm = null;
    const confirmationElement = document.querySelector('#confirmModal');
    const confirmation = window.bootstrap && confirmationElement ? new bootstrap.Modal(confirmationElement) : null;
    document.querySelectorAll('form[data-confirm]').forEach(form => form.addEventListener('submit', event => {
        if (form.dataset.confirmed === 'true') return;
        event.preventDefault();
        if (confirmation) {
            pendingForm = form;
            document.querySelector('#confirmMessage').textContent = form.dataset.confirm;
            confirmation.show();
        } else if (window.confirm(form.dataset.confirm)) {
            form.dataset.confirmed = 'true';
            form.requestSubmit();
        }
    }));
    document.querySelector('#confirmAction')?.addEventListener('click', () => {
        if (pendingForm) {
            pendingForm.dataset.confirmed = 'true';
            confirmation.hide();
            pendingForm.requestSubmit();
            pendingForm = null;
        }
    });
    document.querySelectorAll('form[data-notification-form]').forEach(form => form.addEventListener('submit', async event => {
        event.preventDefault();
        const button = form.querySelector('button');
        button.disabled = true;
        try {
            const response = await fetch(form.action, {
                method: 'POST',
                body: new FormData(form),
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                },
                credentials: 'same-origin'
            });
            if (!response.ok || !response.headers.get('content-type')?.includes('application/json')) throw new Error('Could not update notifications. Please refresh and try again.');
            const result = await response.json();
            document.querySelectorAll('[data-unread-count]').forEach(el => el.textContent = result.unread);
            if (form.closest('[data-notice]')) {
                form.closest('[data-notice]').classList.remove('unread');
                form.remove();
            } else {
                document.querySelectorAll('[data-notice]').forEach(el => {
                    el.classList.remove('unread');
                    el.querySelector('form')?.remove();
                });
                button.disabled = false;
            }
            toast('Notifications marked as read.', 'success');
        } catch (error) {
            toast(error.message, 'error');
            button.disabled = false;
        }
    }));
    document.querySelectorAll('form:not([data-notification-form])').forEach(form => form.addEventListener('submit', event => {
        if (event.defaultPrevented) return;
        const button = event.submitter;
        if (button && form.method.toLowerCase() === 'post') {
            const spinner = document.createElement('span');
            spinner.className = 'button-spinner';
            button.append(spinner);
            button.setAttribute('aria-busy', 'true');
            // Do not disable inputs before the browser constructs the request payload.
            setTimeout(() => button.disabled = true, 0);
        }
    }));
    const makeChart = (canvas, type, data) => {
        if (!window.Chart) return;
        const colors = ['#737fd9', '#b5bdea', '#78b99e', '#edc481', '#ba9dd2', '#e5a1ac', '#8fb9df'];
        if (!data.values.length || !data.values.some(value => value > 0)) {
            const empty = document.createElement('div');
            empty.className = 'empty-state';
            empty.style.padding = '55px 20px';
            empty.textContent = 'No activity to chart yet.';
            canvas.replaceWith(empty);
            return;
        }
        new Chart(canvas, {
            type,
            data: {
                labels: data.labels,
                datasets: [{
                    label: canvas.getAttribute('aria-label'),
                    data: data.values,
                    backgroundColor: type === 'doughnut' ? colors : '#828ddd44',
                    borderColor: type === 'doughnut' ? '#fff' : '#818cd7',
                    borderWidth: type === 'doughnut' ? 4 : 2,
                    borderRadius: type === 'bar' ? 5 : 0,
                    tension: .4,
                    fill: type === 'line'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                animation: prefersReduced ? false : {
                    duration: 650
                },
                cutout: '74%',
                plugins: {
                    legend: {
                        display: type === 'doughnut',
                        position: 'bottom',
                        labels: {
                            usePointStyle: true,
                            pointStyle: 'circle',
                            padding: 20,
                            font: {
                                size: 10
                            }
                        }
                    }
                },
                scales: type === 'doughnut' ? {} : {
                    x: {
                        grid: {
                            display: false
                        },
                        ticks: {
                            font: {
                                size: 9
                            },
                            color: '#9ca4bc'
                        },
                        border: {
                            display: false
                        }
                    },
                    y: {
                        beginAtZero: true,
                        grid: {
                            color: '#f0f2f8'
                        },
                        border: {
                            display: false
                        },
                        ticks: {
                            font: {
                                size: 9
                            },
                            color: '#9ca4bc',
                            precision: 0
                        }
                    }
                }
            }
        });
    };
    document.querySelectorAll('canvas[data-chart]').forEach(canvas => {
        const source = document.getElementById(canvas.dataset.chart);
        if (source) makeChart(canvas, canvas.dataset.chartType, JSON.parse(source.textContent));
    });
    const analyticsSource = document.getElementById('analyticsCharts');
    if (analyticsSource) {
        const charts = JSON.parse(analyticsSource.textContent);
        document.querySelectorAll('canvas[data-analytics-chart]').forEach(canvas => {
            const chart = charts[Number(canvas.dataset.analyticsChart)];
            makeChart(canvas, chart.type, chart.data);
        });
    }
    if ('IntersectionObserver' in window && !prefersReduced) {
        document.documentElement.classList.add('js-reveal');
        const observer = new IntersectionObserver(entries => entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('visible');
                observer.unobserve(entry.target);
            }
        }), {
            threshold: .05
        });
        document.querySelectorAll('.reveal').forEach(element => observer.observe(element));
        const counters = new IntersectionObserver(entries => entries.forEach(entry => {
            if (!entry.isIntersecting) return;
            const target = Number(entry.target.dataset.counter);
            if (!Number.isFinite(target)) return;
            const start = performance.now();
            const update = time => {
                const ratio = Math.min(1, (time - start) / 700);
                entry.target.textContent = Math.round(target * (1 - Math.pow(1 - ratio, 3)));
                if (ratio < 1) requestAnimationFrame(update);
            };
            requestAnimationFrame(update);
            counters.unobserve(entry.target);
        }));
        document.querySelectorAll('[data-counter]').forEach(element => counters.observe(element));
    }
});