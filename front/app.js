(() => {
  const API_BASE_URL = 'http://localhost:8000/api/v1';
  const LOGIN_ENDPOINT = `${API_BASE_URL}/auth/login`;
  const DOCUMENT_TYPES_ENDPOINT = `${API_BASE_URL}/catalogs/document-types?active_only=true`;
  const OWNER_VALIDATION_ENDPOINT = `${API_BASE_URL}/owner-validation/validate`;
  const QUOTE_CREATE_ENDPOINT = `${API_BASE_URL}/quote/create/`;
  const LOGIN_CREDENTIALS = {
    email: 'test@rappi.com',
    password: 'tempralPass123',
  };

  const START_ACTION_SELECTOR = '[data-action="start"]';
  const STORAGE_KEYS = {
    AUTH_TOKEN: 'authToken',
    VALIDATION_RESULT: 'validationResult',
  };

  let authToken = sessionStorage.getItem(STORAGE_KEYS.AUTH_TOKEN) || null;
  const documentTypeMap = new Map();

  function storeToken(token) {
    authToken = token;
    sessionStorage.setItem(STORAGE_KEYS.AUTH_TOKEN, token);
  }

  function clearToken() {
    authToken = null;
    sessionStorage.removeItem(STORAGE_KEYS.AUTH_TOKEN);
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

  function showFeedback(message = '', type = 'info', targetId = 'form-feedback') {
    const feedback = document.getElementById(targetId);
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
        documentTypeMap.set(type.soat_code, type);

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

  function persistValidationResult(data, context = {}) {
    if (!data || typeof data !== 'object') return;

    const payload = {
      is_owner: data.is_owner ?? null,
      message: data.message ?? '',
      owner_info: data.owner_info || null,
      vehicle_info: data.vehicle_info || null,
      session_id: data.session_id || null,
      context: {
        documentLabel: context.documentLabel || null,
        documentTypeCode: context.documentTypeCode || null,
        documentNumber: context.documentNumber || null,
        licensePlate: context.licensePlate || null,
      },
    };

    sessionStorage.setItem(STORAGE_KEYS.VALIDATION_RESULT, JSON.stringify(payload));
  }

  function loadValidationResult() {
    const raw = sessionStorage.getItem(STORAGE_KEYS.VALIDATION_RESULT);
    if (!raw) return null;

    try {
      return JSON.parse(raw);
    } catch (error) {
      console.warn('No se pudo interpretar la validación almacenada:', error);
      return null;
    }
  }

  function clearValidationResult() {
    sessionStorage.removeItem(STORAGE_KEYS.VALIDATION_RESULT);
  }

  function redirectToCotizador() {
    window.location.replace('cotizador.html');
  }

  function formatCylinderCapacity(value) {
    const numeric = Number(value);
    if (Number.isFinite(numeric) && numeric > 0) {
      return `${numeric.toLocaleString('es-CO')} cc`;
    }
    return 'No disponible';
  }

  function formatFuelType(value) {
    if (!value) return 'No disponible';
    return value.toString().trim().toUpperCase();
  }

  function formatCurrency(value) {
    const numeric = Number(value);
    if (!Number.isFinite(numeric)) {
      return '$0';
    }

    return numeric.toLocaleString('es-CO', {
      style: 'currency',
      currency: 'COP',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    });
  }

  function setTextContent(id, value) {
    const element = document.getElementById(id);
    if (element) {
      element.textContent = value || 'No disponible';
    }
  }

  function setPageLoading(isLoading, message = 'Generando tu cotización…') {
    const overlay = document.getElementById('page-loader');
    if (!overlay) return;

    const messageElement = overlay.querySelector('.page-loader__message');
    if (messageElement) {
      messageElement.textContent = message;
    }

    overlay.hidden = !isLoading;
    document.body.classList.toggle('is-loading', isLoading);
  }

  function setHomologationsDisabled(container, disabled) {
    if (!container) return;

    container.querySelectorAll('input[type="radio"]').forEach((input) => {
      input.disabled = disabled;
      if (input.parentElement) {
        input.parentElement.classList.toggle('is-disabled', disabled);
      }
    });
  }

  function updateHomologationSelection(container) {
    const cards = container?.querySelectorAll('.homologation-card');
    if (!cards) return;

    cards.forEach((card) => {
      const input = card.querySelector('input[type="radio"]');
      if (!input) return;
      if (input.checked) {
        card.classList.add('homologation-card--selected');
      } else {
        card.classList.remove('homologation-card--selected');
      }
    });
  }

  function renderHomologations(container, homologations = [], onSelect) {
    if (!container) return;

    container.innerHTML = '';

    if (!Array.isArray(homologations) || homologations.length === 0) {
      const empty = document.createElement('p');
      empty.className = 'empty-state';
      empty.textContent = 'No encontramos clases disponibles para cotizar este vehículo.';
      container.appendChild(empty);
      return;
    }

    homologations.forEach((item) => {
      if (!item?.class_code) return;

      const card = document.createElement('label');
      card.className = 'homologation-card';

      const input = document.createElement('input');
      input.type = 'radio';
      input.name = 'homologation';
      input.value = item.class_code;
      input.required = true;
      input.addEventListener('change', () => {
        updateHomologationSelection(container);
        if (typeof onSelect === 'function' && input.checked) {
          onSelect(item, input);
        }
      });

      const title = document.createElement('span');
      title.className = 'homologation-card__title';
      title.textContent = item.class_description || `Clase ${item.class_code}`;

      const code = document.createElement('span');
      code.className = 'homologation-card__code';
      code.textContent = `Código ${item.class_code}`;

      card.appendChild(input);
      card.appendChild(title);
      card.appendChild(code);

      container.appendChild(card);
    });

    updateHomologationSelection(container);
  }

  function renderQuoteProducts(products = []) {
    const section = document.getElementById('products-section');
    const list = document.getElementById('products-list');
    const highlight = document.getElementById('soat-highlight');
    const priceElement = document.getElementById('soat-price');
    const labelElement = document.getElementById('soat-plan-label');
    const detailsElement = document.getElementById('soat-plan-details');

    if (!section || !list || !highlight || !priceElement || !labelElement || !detailsElement) {
      return;
    }

    list.innerHTML = '';
    detailsElement.innerHTML = '';

    if (!Array.isArray(products) || products.length === 0) {
      section.hidden = true;
      highlight.hidden = true;
      labelElement.textContent = 'Selecciona una clase para ver tu tarifa.';
      priceElement.textContent = '$0';
      return;
    }

    section.hidden = false;

    const soatProduct = products.find((product) => (product?.product_code || '').toUpperCase() === 'SOAT');
    const soatPlan = soatProduct?.plans?.[0];
    const soatTotal = soatPlan?.policy_total_value ?? soatPlan?.total_to_pay;

    if (soatProduct && soatPlan && Number.isFinite(Number(soatTotal))) {
      priceElement.textContent = formatCurrency(soatTotal);
      labelElement.textContent = 'Valor total a pagar por tu SOAT';

      const detailEntries = [
        {
          label: 'Periodo de vigencia',
          value:
            soatPlan.start_date && soatPlan.end_date
              ? `${soatPlan.start_date} — ${soatPlan.end_date}`
              : null,
        },
        {
          label: 'Prima',
          value: formatCurrency(soatPlan.premium_value),
        },
        {
          label: 'Contribución ADRES',
          value: formatCurrency(soatPlan.contribution_value),
        },
        {
          label: 'Tasa RUNT',
          value: formatCurrency(soatPlan.runt_fee),
        },
      ].filter((entry) => entry.value);

      detailsElement.innerHTML = '';
      detailEntries.forEach((entry) => {
        const wrapper = document.createElement('div');
        const dt = document.createElement('dt');
        dt.textContent = entry.label;
        const dd = document.createElement('dd');
        dd.textContent = entry.value;
        wrapper.appendChild(dt);
        wrapper.appendChild(dd);
        detailsElement.appendChild(wrapper);
      });

      highlight.hidden = false;
    } else {
      priceElement.textContent = '$0';
      labelElement.textContent = 'Selecciona una clase para ver tu tarifa.';
      highlight.hidden = true;
    }

    products.forEach((product) => {
      if (!product) return;

      const card = document.createElement('article');
      card.className = 'product-card';
      if (!product.mandatory) {
        card.classList.add('product-card--optional');
      }

      const header = document.createElement('div');
      header.className = 'product-card__header';

      const title = document.createElement('h3');
      title.className = 'product-card__title';
      title.textContent = product.product_name || product.product_code || 'Producto';

      const badge = document.createElement('span');
      badge.className = 'product-card__badge';
      badge.textContent = product.mandatory ? 'Incluido' : 'Opcional';

      header.appendChild(title);
      header.appendChild(badge);
      card.appendChild(header);

      const plansWrapper = document.createElement('div');
      plansWrapper.className = 'product-card__plans';

      if (Array.isArray(product.plans) && product.plans.length > 0) {
        product.plans.forEach((plan) => {
          const planElement = document.createElement('article');
          planElement.className = 'product-plan';

          const planTitle = document.createElement('h4');
          planTitle.className = 'product-plan__title';
          planTitle.textContent = plan.desc_type || plan.option_name || plan.code_type || 'Plan';

          const meta = document.createElement('p');
          meta.className = 'product-plan__meta';
          if (plan.year_validity || plan.issue_date) {
            const metaParts = [];
            if (plan.year_validity) metaParts.push(`Vigencia ${plan.year_validity}`);
            if (plan.issue_date) metaParts.push(`Expedición ${plan.issue_date}`);
            meta.textContent = metaParts.join(' · ');
          } else {
            meta.textContent = product.product_code === 'SOAT' ? 'Cobertura obligatoria' : 'Cobertura adicional';
          }

          const stats = document.createElement('dl');
          stats.className = 'product-plan__stats';

          function addStat(label, value) {
            if (!value && value !== 0) return;
            const row = document.createElement('div');
            const dt = document.createElement('dt');
            dt.textContent = label;
            const dd = document.createElement('dd');
            dd.textContent = value;
            row.appendChild(dt);
            row.appendChild(dd);
            stats.appendChild(row);
          }

          if ((product.product_code || '').toUpperCase() === 'SOAT') {
            addStat('Total a pagar', formatCurrency(plan.total_to_pay ?? plan.policy_total_value));
            addStat('Prima', formatCurrency(plan.premium_value));
            addStat('Contribución', formatCurrency(plan.contribution_value));
            addStat('RUNT', formatCurrency(plan.runt_fee));
          } else if ((product.product_code || '').toUpperCase() === 'AP') {
            const prices = plan.prices || {};
            addStat('Valor asegurado', formatCurrency(prices.insured_value));
            addStat('Prima', formatCurrency(prices.policy_value));
            addStat('Asistencias', formatCurrency(prices.assistance_value));
          } else {
            addStat('Precio', formatCurrency(plan.policy_total_value || plan.total_to_pay));
          }

          planElement.appendChild(planTitle);
          if (meta.textContent) {
            planElement.appendChild(meta);
          }
          planElement.appendChild(stats);

          plansWrapper.appendChild(planElement);
        });
      } else {
        const emptyPlans = document.createElement('p');
        emptyPlans.className = 'product-plan__meta';
        emptyPlans.textContent = 'No encontramos planes asociados a este producto.';
        plansWrapper.appendChild(emptyPlans);
      }

      card.appendChild(plansWrapper);

      if (!product.mandatory) {
        const toggle = document.createElement('label');
        toggle.className = 'product-card__toggle';
        const checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        checkbox.name = `product-${product.product_code || 'adicional'}`;
        checkbox.value = product.product_code || '';
        checkbox.checked = false;
        const toggleText = document.createElement('span');
        toggleText.textContent = 'Agregar a mi compra';
        toggle.appendChild(checkbox);
        toggle.appendChild(toggleText);
        card.appendChild(toggle);
      }

      list.appendChild(card);
    });
  }

  function initVehicleDetailPage() {
    const page = document.querySelector('[data-page="vehicle-detail"]');
    if (!page) return;

    const validation = loadValidationResult();
    const vehicleInfo = validation?.vehicle_info;
    const ownerInfo = validation?.owner_info;
    const context = validation?.context || {};

    if (!validation || !vehicleInfo || !validation.session_id) {
      redirectToCotizador();
      return;
    }

    const message = validation.message || 'Selecciona la clase adecuada para continuar con la cotización.';
    setTextContent('validation-message', message);
    setTextContent('owner-full-name', ownerInfo?.full_name || [ownerInfo?.first_name, ownerInfo?.last_name, ownerInfo?.second_last_name]
      .filter(Boolean)
      .join(' '));
    setTextContent('owner-document', context.documentNumber || ownerInfo?.document_number);
    setTextContent('owner-document-type', context.documentLabel || ownerInfo?.document_type);

    setTextContent('vehicle-brand', vehicleInfo.brand);
    setTextContent('vehicle-plate', (context.licensePlate || vehicleInfo.license_plate || '').toString().toUpperCase());
    setTextContent('vehicle-model', vehicleInfo.year || 'No disponible');
    setTextContent('vehicle-line', vehicleInfo.model);
    setTextContent('vehicle-cylinder', formatCylinderCapacity(vehicleInfo.cylinder_capacity));
    setTextContent('vehicle-fuel', formatFuelType(vehicleInfo.fuel_type));

    const homologations = Array.isArray(vehicleInfo.homologations) ? vehicleInfo.homologations : [];
    const homologationContainer = document.getElementById('homologations-list');
    const feedbackId = 'quote-feedback';

    renderQuoteProducts([]);

    if (!homologationContainer) {
      showFeedback('No pudimos preparar la selección de clases para cotizar.', 'error', feedbackId);
      return;
    }

    if (homologations.length === 0) {
      renderHomologations(homologationContainer, homologations);
      showFeedback('No encontramos clases disponibles para este vehículo. Vuelve al paso anterior.', 'error', feedbackId);
      return;
    }

    let quoteInProgress = false;

    async function executeQuote(classCode) {
      if (quoteInProgress) {
        return;
      }

      if (!classCode) {
        showFeedback('Selecciona una clase válida para continuar.', 'error', feedbackId);
        return;
      }

      if (!validation.session_id) {
        showFeedback('La sesión de cotización no es válida. Vuelve a ingresar tus datos.', 'error', feedbackId);
        clearValidationResult();
        redirectToCotizador();
        return;
      }

      quoteInProgress = true;
      setPageLoading(true, 'Cotizando la clase seleccionada…');
      setHomologationsDisabled(homologationContainer, true);
      showFeedback('Cotizando la clase seleccionada…', 'info', feedbackId);

      try {
        const response = await authorizedFetch(QUOTE_CREATE_ENDPOINT, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            class_code: classCode,
            products: ['SOAT', 'AP'],
            session_id: validation.session_id,
          }),
        });

        if (!response.ok) {
          const message = (await extractErrorMessage(response)) || 'No pudimos generar la cotización.';
          throw new Error(message);
        }

        const quote = await response.json().catch(() => ({}));
        renderQuoteProducts(Array.isArray(quote?.products) ? quote.products : []);
        const successMessage = quote?.message || 'Cotización generada correctamente.';
        showFeedback(successMessage, 'success', feedbackId);
      } catch (error) {
        console.error('Error al generar la cotización:', error);
        renderQuoteProducts([]);
        showFeedback(error?.message || 'Ocurrió un problema al generar la cotización. Intenta nuevamente.', 'error', feedbackId);
      } finally {
        quoteInProgress = false;
        setPageLoading(false);
        setHomologationsDisabled(homologationContainer, false);
      }
    }

    renderHomologations(homologationContainer, homologations, (item) => {
      if (!item?.class_code) return;
      executeQuote(item.class_code);
    });

    showFeedback(
      'Selecciona la clase que mejor represente el uso de tu vehículo para generar la cotización.',
      'info',
      feedbackId
    );
  }

  function initCotizadorForm() {
    const form = document.querySelector('#cotizacion-form');
    if (!form) return;

    clearValidationResult();

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

        if (!data?.vehicle_info || !data?.session_id) {
          throw new Error('No recibimos la información del vehículo para continuar con la cotización. Intenta nuevamente.');
        }
        const documentType = documentTypeMap.get(documentTypeCode);
        const documentLabel = documentType?.name || 'Documento';

        persistValidationResult(data, {
          documentLabel,
          documentTypeCode,
          documentNumber,
          licensePlate,
        });

        window.location.href = 'detalle.html';
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
    initVehicleDetailPage();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
