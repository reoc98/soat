(() => {
  const API_BASE_URL = 'http://localhost:8000/api/v1';
  const LOGIN_ENDPOINT = `${API_BASE_URL}/auth/login`;
  const DOCUMENT_TYPES_ENDPOINT = `${API_BASE_URL}/catalogs/document-types?active_only=true`;
  const OWNER_VALIDATION_ENDPOINT = `${API_BASE_URL}/owner-validation/validate`;
  const LOGIN_CREDENTIALS = {
    email: 'test@rappi.com',
    password: 'tempralPass123',
  };

  const START_ACTION_SELECTOR = '[data-action="start"]';

  let authToken = sessionStorage.getItem('authToken') || null;
  const documentTypeMap = new Map();

  function storeToken(token) {
    authToken = token;
    sessionStorage.setItem('authToken', token);
  }

  function clearToken() {
    authToken = null;
    sessionStorage.removeItem('authToken');
  }

  async function login() {
    const response = await fetch(LOGIN_ENDPOINT, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(LOGIN_CREDENTIALS),
    });

    if (!response.ok) {
      const message = (await extractErrorMessage(response)) || 'No pudimos iniciar sesión.';
      throw new Error(message);
    }

    const payload = await response.json();
    const token = payload?.id_token;

    if (!token) {
      throw new Error('El servicio no retornó un token válido.');
    }

    storeToken(token);
    return token;
  }

  async function ensureAuthToken() {
    if (authToken) {
      return authToken;
    }

    return login();
  }

  async function authorizedFetch(url, options = {}, retry = true) {
    const token = await ensureAuthToken();
    const headers = {
      ...(options.headers || {}),
      Authorization: `Bearer ${token}`,
    };

    const response = await fetch(url, {
      ...options,
      headers,
    });

    if (response.status === 401 && retry) {
      clearToken();
      return authorizedFetch(url, options, false);
    }

    return response;
  }

  async function extractErrorMessage(response) {
    if (!response) return null;

    try {
      const data = await response.clone().json();
      return data?.message || data?.detail || data?.error || null;
    } catch (jsonError) {
      try {
        const text = await response.clone().text();
        return text || null;
      } catch (textError) {
        return null;
      }
    }
  }

  function setButtonLoading(element, isLoading, loadingText = 'Cargando...') {
    if (!(element instanceof HTMLElement)) return;

    if (isLoading) {
      if (!element.dataset.originalLabel) {
        element.dataset.originalLabel = element.textContent?.trim() || '';
      }
      element.textContent = loadingText;
      element.classList.add('is-loading');
      element.setAttribute('aria-busy', 'true');
      element.setAttribute('aria-disabled', 'true');
      if (element.tagName === 'BUTTON') {
        element.disabled = true;
      }
    } else {
      const original = element.dataset.originalLabel || '';
      element.textContent = original;
      element.classList.remove('is-loading');
      element.removeAttribute('aria-busy');
      element.removeAttribute('aria-disabled');
      if (element.tagName === 'BUTTON') {
        element.disabled = false;
      }
      delete element.dataset.originalLabel;
    }
  }

  function showFeedback(message = '', type = 'info') {
    const feedback = document.getElementById('form-feedback');
    if (!feedback) return;

    if (!message) {
      feedback.textContent = '';
      feedback.className = 'form__feedback';
      return;
    }

    feedback.textContent = message;
    feedback.className = `form__feedback form__feedback--visible form__feedback--${type}`;
  }

  function getRedirectUrl(element) {
    return element?.dataset?.target || element?.getAttribute('href') || 'cotizador.html';
  }

  function initStartButtons() {
    const startButtons = document.querySelectorAll(START_ACTION_SELECTOR);
    startButtons.forEach((button) => {
      button.addEventListener('click', async (event) => {
        event.preventDefault();
        if (button.classList.contains('is-loading')) {
          return;
        }

        const redirectUrl = getRedirectUrl(button);
        setButtonLoading(button, true, 'Ingresando...');

        try {
          await login();
          window.location.href = redirectUrl;
        } catch (error) {
          console.error('Error al iniciar sesión:', error);
          setButtonLoading(button, false);
          window.alert(error?.message || 'Hubo un problema al iniciar sesión. Inténtalo nuevamente.');
        }
      });
    });
  }

  async function loadDocumentTypes(select) {
    try {
      const response = await authorizedFetch(DOCUMENT_TYPES_ENDPOINT);

      if (!response.ok) {
        const message = (await extractErrorMessage(response)) || 'No pudimos cargar los tipos de documento.';
        throw new Error(message);
      }

      const data = await response.json();
      const documentTypes = Array.isArray(data?.document_types) ? data.document_types : [];

      documentTypeMap.clear();
      select.innerHTML = '';

      const defaultOption = document.createElement('option');
      defaultOption.value = '';
      defaultOption.textContent = documentTypes.length
        ? 'Selecciona una opción'
        : 'No hay tipos de documento disponibles';
      defaultOption.disabled = documentTypes.length === 0;
      defaultOption.selected = true;
      select.appendChild(defaultOption);

      documentTypes.forEach((type) => {
        if (!type?.soat_code || !type?.name) return;
        documentTypeMap.set(type.soat_code, type.name);

        const option = document.createElement('option');
        option.value = type.soat_code;
        option.textContent = type.name;
        select.appendChild(option);
      });

      select.disabled = documentTypes.length === 0;

      if (documentTypes.length === 0) {
        showFeedback('No encontramos tipos de documento activos para continuar.', 'error');
      } else {
        showFeedback('Completa la información para generar tu cotización.', 'info');
      }
    } catch (error) {
      console.error('Error al cargar tipos de documento:', error);
      select.innerHTML = '';
      const option = document.createElement('option');
      option.value = '';
      option.textContent = 'Error al cargar tipos de documento';
      option.disabled = true;
      option.selected = true;
      select.appendChild(option);
      select.disabled = true;
      showFeedback(error?.message || 'No pudimos cargar los tipos de documento. Intenta nuevamente.', 'error');
    }
  }

  function initDocumentTypeSelect() {
    const select = document.querySelector('select[name="documentType"]');
    if (!select) return;

    loadDocumentTypes(select);
  }

  function formatLicensePlate(value) {
    return (value || '').toString().trim().toUpperCase();
  }

  function formatDocumentNumber(value) {
    return (value || '').toString().trim();
  }

  function initCotizadorForm() {
    const form = document.querySelector('#cotizacion-form');
    if (!form) return;

    const submitButton = form.querySelector('button[type="submit"]');

    form.addEventListener('submit', async (event) => {
      event.preventDefault();

      if (!form.checkValidity()) {
        form.reportValidity();
        return;
      }

      const formData = new FormData(form);
      const licensePlate = formatLicensePlate(formData.get('placa'));
      const documentTypeCode = formatDocumentNumber(formData.get('documentType'));
      const documentNumber = formatDocumentNumber(formData.get('documentNumber'));

      if (!licensePlate || !documentTypeCode || !documentNumber) {
        showFeedback('Por favor completa todos los campos obligatorios.', 'error');
        return;
      }

      if (submitButton) {
        setButtonLoading(submitButton, true, 'Validando...');
      }
      showFeedback('Validando la información del propietario…', 'info');

      try {
        const response = await authorizedFetch(
          OWNER_VALIDATION_ENDPOINT,
          {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({
              document_number: documentNumber,
              document_type: documentTypeCode,
              license_plate: licensePlate,
            }),
          }
        );

        if (!response.ok) {
          const message = (await extractErrorMessage(response)) || 'No pudimos validar los datos. Intenta nuevamente.';
          throw new Error(message);
        }

        const data = await response.json().catch(() => ({}));
        const documentLabel = documentTypeMap.get(documentTypeCode) || 'Documento';
        const validationMessage = data?.message || 'Validación exitosa.';

        showFeedback(
          `${validationMessage} ${documentLabel}: ${documentNumber} · Placa ${licensePlate}. Continúa con tu cotización.`,
          'success'
        );
      } catch (error) {
        console.error('Error al validar propietario:', error);
        showFeedback(error?.message || 'Ocurrió un error al validar los datos. Intenta nuevamente.', 'error');
      } finally {
        if (submitButton) {
          setButtonLoading(submitButton, false);
        }
      }
    });
  }

  function init() {
    initStartButtons();
    initDocumentTypeSelect();
    initCotizadorForm();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
