(() => {
  const API_BASE_URL = 'http://localhost:8000/api/v1';
  const LOGIN_ENDPOINT = `${API_BASE_URL}/auth/login`;
  const DOCUMENT_TYPES_ENDPOINT = `${API_BASE_URL}/catalogs/document-types?active_only=true`;
  const CITIES_ENDPOINT = `${API_BASE_URL}/catalogs/cities?active_only=true`;
  const GENDERS_ENDPOINT = `${API_BASE_URL}/catalogs/genders?active_only=true`;
  const OWNER_VALIDATION_ENDPOINT = `${API_BASE_URL}/owner-validation/validate`;
  const QUOTE_CREATE_ENDPOINT = `${API_BASE_URL}/quote/create/`;
  const PRE_EXPEDITION_ENDPOINT = (sessionId) =>
    `${API_BASE_URL}/expedition/pre-expedition/${encodeURIComponent(sessionId)}`;
  const LOGIN_CREDENTIALS = {
    email: 'test@rappi.com',
    password: 'tempralPass123',
  };

  const START_ACTION_SELECTOR = '[data-action="start"]';
  const STORAGE_KEYS = {
    AUTH_TOKEN: 'authToken',
    VALIDATION_RESULT: 'validationResult',
    QUOTE_RESULT: 'quoteResult',
    PRE_EXPEDITION: 'preExpedition',
    PAYMENT_STATUS: 'paymentStatus',
  };

  const defaultQuoteState = {
    classCode: null,
    classDescription: '',
    products: [],
    selections: [],
    sessionId: null,
  };

  let quoteState = { ...defaultQuoteState };

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

  function sanitizeSelections(selections) {
    if (!Array.isArray(selections)) {
      return [];
    }

    return selections
      .filter((item) => item && typeof item === 'object')
      .map((item) => ({
        product_code: (item.product_code || '').toString().toUpperCase(),
        option_id: item.option_id ?? null,
        mandatory: Boolean(item.mandatory),
        selected: Boolean(item.selected ?? item.mandatory ?? false),
        product_name: item.product_name || '',
        plan_name: item.plan_name || '',
      }));
  }

  function setQuoteState(state = {}) {
    quoteState = {
      classCode: state?.classCode || null,
      classDescription: state?.classDescription || '',
      products: Array.isArray(state?.products) ? state.products : [],
      selections: sanitizeSelections(state?.selections),
      sessionId: state?.sessionId || null,
    };
  }

  function persistQuoteState(state = quoteState) {
    sessionStorage.setItem(
      STORAGE_KEYS.QUOTE_RESULT,
      JSON.stringify({
        classCode: state.classCode,
        classDescription: state.classDescription,
        products: state.products,
        selections: state.selections,
        sessionId: state.sessionId,
      })
    );
  }

  function loadQuoteState() {
    const raw = sessionStorage.getItem(STORAGE_KEYS.QUOTE_RESULT);
    if (!raw) return null;

    try {
      const stored = JSON.parse(raw);
      return {
        classCode: stored?.classCode || null,
        classDescription: stored?.classDescription || '',
        products: Array.isArray(stored?.products) ? stored.products : [],
        selections: sanitizeSelections(stored?.selections),
        sessionId: stored?.sessionId || null,
      };
    } catch (error) {
      console.warn('No se pudo interpretar la cotización almacenada:', error);
      return null;
    }
  }

  function clearQuoteState() {
    sessionStorage.removeItem(STORAGE_KEYS.QUOTE_RESULT);
    quoteState = { ...defaultQuoteState };
  }

  function getSelectionByProductCode(productCode) {
    if (!productCode) return null;
    const normalized = productCode.toString().toUpperCase();
    return (
      quoteState.selections.find((selection) => selection.product_code === normalized) || null
    );
  }

  function updateProductSelection(productCode, updates = {}) {
    if (!productCode) return;
    const normalized = productCode.toString().toUpperCase();
    quoteState.selections = quoteState.selections.map((selection) => {
      if (selection.product_code !== normalized) {
        return selection;
      }

      const nextSelection = {
        ...selection,
        ...updates,
      };
      return {
        ...nextSelection,
        selected: Boolean(nextSelection.selected || nextSelection.mandatory),
      };
    });
    persistQuoteState();
  }

  function getSelectedSelections() {
    return quoteState.selections.filter((selection) => selection.selected);
  }

  function persistPreExpeditionState(state = {}) {
    sessionStorage.setItem(STORAGE_KEYS.PRE_EXPEDITION, JSON.stringify(state));
  }

  function loadPreExpeditionState() {
    const raw = sessionStorage.getItem(STORAGE_KEYS.PRE_EXPEDITION);
    if (!raw) return null;

    try {
      return JSON.parse(raw);
    } catch (error) {
      console.warn('No se pudo interpretar la información de pre-expedición almacenada:', error);
      return null;
    }
  }

  function clearPreExpeditionState() {
    sessionStorage.removeItem(STORAGE_KEYS.PRE_EXPEDITION);
  }

  function setPaymentStatus(status = 'pending', metadata = {}) {
    sessionStorage.setItem(
      STORAGE_KEYS.PAYMENT_STATUS,
      JSON.stringify({
        status,
        ...metadata,
      })
    );
  }

  function loadPaymentStatus() {
    const raw = sessionStorage.getItem(STORAGE_KEYS.PAYMENT_STATUS);
    if (!raw) return null;

    try {
      return JSON.parse(raw);
    } catch (error) {
      console.warn('No se pudo interpretar el estado de pago almacenado:', error);
      return null;
    }
  }

  function clearPaymentStatus() {
    sessionStorage.removeItem(STORAGE_KEYS.PAYMENT_STATUS);
  }

  function redirectToCotizador() {
    window.location.replace('cotizador.html');
  }

  function redirectToDetalle() {
    window.location.replace('detalle.html');
  }

  function redirectToResumen() {
    window.location.replace('resumen.html');
  }

  function redirectToPago() {
    window.location.replace('pago.html');
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

  function buildSelectionsFromProducts(products = []) {
    const mapped = [];

    products.forEach((product) => {
      if (!product) return;
      const productCode = (product.product_code || '').toString().toUpperCase();
      const firstPlan = Array.isArray(product.plans) ? product.plans[0] : null;

      if (!productCode || !firstPlan?.option_id) {
        return;
      }

      mapped.push({
        product_code: productCode,
        option_id: firstPlan.option_id,
        mandatory: Boolean(product.mandatory ?? true),
        selected: Boolean(product.mandatory ?? true),
        product_name: product.product_name || productCode,
        plan_name: firstPlan.desc_type || firstPlan.option_name || firstPlan.code_type || '',
      });
    });

    return sanitizeSelections(mapped);
  }

  function getPrimaryPlan(product) {
    if (!product) return null;
    const plans = Array.isArray(product.plans) ? product.plans : [];
    return plans.length > 0 ? plans[0] : null;
  }

  function getPlanPrice(product, plan) {
    if (!plan) return 0;
    const code = (product?.product_code || '').toString().toUpperCase();

    if (code === 'SOAT') {
      const total = plan.policy_total_value ?? plan.total_to_pay ?? 0;
      return Number(total) || 0;
    }

    if (code === 'AP') {
      const prices = plan?.prices || {};
      return Number(prices.policy_value ?? prices.total ?? prices.assistance_value ?? 0) || 0;
    }

    return Number(plan.policy_total_value ?? plan.total_to_pay ?? 0) || 0;
  }

  function getPlanStats(productCode, plan) {
    const normalized = (productCode || '').toString().toUpperCase();
    const stats = [];

    if (!plan) {
      return stats;
    }

    if (normalized === 'SOAT') {
      stats.push(
        { label: 'Prima', value: formatCurrency(plan.premium_value) },
        { label: 'Contribución', value: formatCurrency(plan.contribution_value) },
        { label: 'Tasa RUNT', value: formatCurrency(plan.runt_fee) }
      );
    } else if (normalized === 'AP') {
      const prices = plan?.prices || {};
      stats.push(
        { label: 'Valor asegurado', value: formatCurrency(prices.insured_value) },
        { label: 'Prima', value: formatCurrency(prices.policy_value) },
        { label: 'Asistencias', value: formatCurrency(prices.assistance_value) }
      );
    }

    return stats.filter((stat) => stat.value && stat.value !== '$0');
  }

  function getSelectedProductDetails() {
    const selectionsMap = new Map();
    quoteState.selections.forEach((selection) => {
      selectionsMap.set(selection.product_code, selection);
    });

    return quoteState.products
      .map((product) => {
        if (!product) return null;
        const code = (product.product_code || '').toString().toUpperCase();
        const selection = selectionsMap.get(code);
        if (!selection?.selected) return null;
        const plan = getPrimaryPlan(product);
        return {
          product,
          plan,
          selection,
          code,
          price: getPlanPrice(product, plan),
          stats: getPlanStats(code, plan),
        };
      })
      .filter(Boolean);
  }

  function getQuoteTotal() {
    return getSelectedProductDetails().reduce((acc, item) => acc + (Number(item.price) || 0), 0);
  }

  function renderSelectedProducts(listOrId, totalOrId, { emptyMessage } = {}) {
    const list =
      typeof listOrId === 'string' ? document.getElementById(listOrId) : listOrId;
    const totalElement =
      typeof totalOrId === 'string' ? document.getElementById(totalOrId) : totalOrId;

    if (!list) return;

    const selectedDetails = getSelectedProductDetails();
    list.innerHTML = '';

    if (!selectedDetails.length) {
      const emptyItem = document.createElement('li');
      emptyItem.className = 'summary-product summary-product--empty';
      emptyItem.textContent =
        emptyMessage || 'No encontramos coberturas seleccionadas. Regresa al paso anterior.';
      list.appendChild(emptyItem);
      if (totalElement) {
        totalElement.textContent = formatCurrency(0);
      }
      return;
    }

    selectedDetails.forEach((detail) => {
      const item = document.createElement('li');
      item.className = 'summary-product';
      if (!detail.selection.mandatory) {
        item.classList.add('summary-product--optional');
      }

      const header = document.createElement('div');
      header.className = 'summary-product__header';

      const title = document.createElement('h3');
      title.className = 'summary-product__title';
      title.textContent = detail.product.product_name || detail.code;
      header.appendChild(title);

      const badge = document.createElement('span');
      badge.className = 'summary-product__badge';
      badge.textContent = detail.selection.mandatory ? 'Incluido' : 'Opcional';
      header.appendChild(badge);

      const price = document.createElement('span');
      price.className = 'summary-product__price';
      price.textContent = formatCurrency(detail.price);
      header.appendChild(price);

      item.appendChild(header);

      const planName =
        detail.plan?.desc_type || detail.plan?.option_name || detail.plan?.code_type || '';
      if (planName) {
        const planInfo = document.createElement('p');
        planInfo.className = 'summary-product__plan';
        planInfo.textContent = planName;
        item.appendChild(planInfo);
      }

      if (detail.stats.length > 0) {
        const statsList = document.createElement('dl');
        statsList.className = 'summary-product__stats';
        detail.stats.forEach((stat) => {
          const row = document.createElement('div');
          const dt = document.createElement('dt');
          dt.textContent = stat.label;
          const dd = document.createElement('dd');
          dd.textContent = stat.value;
          row.appendChild(dt);
          row.appendChild(dd);
          statsList.appendChild(row);
        });
        item.appendChild(statsList);
      }

      list.appendChild(item);
    });

    if (totalElement) {
      totalElement.textContent = formatCurrency(getQuoteTotal());
    }
  }

  function toggleBirthDateField(isVisible) {
    const field = document.getElementById('field-birthdate');
    if (!field) return;

    const input = field.querySelector('input[name="birthDate"]');
    field.toggleAttribute('hidden', !isVisible);
    field.classList.toggle('is-hidden', !isVisible);
    if (input) {
      input.required = Boolean(isVisible);
      if (!isVisible) {
        input.value = '';
      }
    }
  }

  function isProductSelected(productCode) {
    const selection = getSelectionByProductCode(productCode);
    return Boolean(selection?.selected);
  }

  async function loadCitiesSelect(select) {
    if (!select) return [];

    select.innerHTML = '';
    const loadingOption = document.createElement('option');
    loadingOption.value = '';
    loadingOption.textContent = 'Cargando ciudades...';
    loadingOption.disabled = true;
    loadingOption.selected = true;
    select.appendChild(loadingOption);
    select.disabled = true;

    try {
      const response = await authorizedFetch(CITIES_ENDPOINT);
      if (!response.ok) {
        const message = (await extractErrorMessage(response)) || 'No pudimos cargar las ciudades.';
        throw new Error(message);
      }

      const data = await response.json().catch(() => ({}));
      const cities = Array.isArray(data?.cities) ? data.cities : [];

      select.innerHTML = '';
      const placeholder = document.createElement('option');
      placeholder.value = '';
      placeholder.textContent = cities.length
        ? 'Selecciona una ciudad'
        : 'No hay ciudades disponibles';
      placeholder.disabled = true;
      placeholder.selected = true;
      select.appendChild(placeholder);

      cities.forEach((city) => {
        if (!city?.id) return;
        const option = document.createElement('option');
        option.value = city.id;
        const department = city.department_name ? ` - ${city.department_name}` : '';
        option.textContent = `${city.name || 'Ciudad'}${department}`;
        select.appendChild(option);
      });

      select.disabled = cities.length === 0;
      return cities;
    } catch (error) {
      console.error('Error al cargar ciudades:', error);
      select.innerHTML = '';
      const option = document.createElement('option');
      option.value = '';
      option.textContent = 'No pudimos cargar las ciudades';
      option.disabled = true;
      option.selected = true;
      select.appendChild(option);
      select.disabled = true;
      showFeedback(
        error?.message || 'No pudimos cargar las ciudades. Intenta nuevamente.',
        'error',
        'summary-feedback'
      );
      return [];
    }
  }

  async function loadGendersSelect(select) {
    if (!select) return [];

    select.innerHTML = '';
    const loadingOption = document.createElement('option');
    loadingOption.value = '';
    loadingOption.textContent = 'Cargando géneros...';
    loadingOption.disabled = true;
    loadingOption.selected = true;
    select.appendChild(loadingOption);
    select.disabled = true;

    try {
      const response = await authorizedFetch(GENDERS_ENDPOINT);
      if (!response.ok) {
        const message = (await extractErrorMessage(response)) || 'No pudimos cargar los géneros.';
        throw new Error(message);
      }

      const data = await response.json().catch(() => ({}));
      const genders = Array.isArray(data?.genders) ? data.genders : [];

      select.innerHTML = '';
      const placeholder = document.createElement('option');
      placeholder.value = '';
      placeholder.textContent = genders.length
        ? 'Selecciona un género'
        : 'No hay géneros disponibles';
      placeholder.disabled = true;
      placeholder.selected = true;
      select.appendChild(placeholder);

      genders.forEach((gender) => {
        if (!gender?.id) return;
        const option = document.createElement('option');
        option.value = gender.id;
        option.textContent = gender.name || gender.code || 'Opción';
        select.appendChild(option);
      });

      select.disabled = genders.length === 0;
      return genders;
    } catch (error) {
      console.error('Error al cargar géneros:', error);
      select.innerHTML = '';
      const option = document.createElement('option');
      option.value = '';
      option.textContent = 'No pudimos cargar los géneros';
      option.disabled = true;
      option.selected = true;
      select.appendChild(option);
      select.disabled = true;
      showFeedback(
        error?.message || 'No pudimos cargar los géneros. Intenta nuevamente.',
        'error',
        'summary-feedback'
      );
      return [];
    }
  }

  function prepareQuoteState(homologation = {}, products = [], sessionId = quoteState.sessionId) {
    setQuoteState({
      classCode: homologation?.class_code || homologation?.classCode || null,
      classDescription: homologation?.class_description || homologation?.classDescription || '',
      products: Array.isArray(products) ? products : [],
      selections: buildSelectionsFromProducts(products),
      sessionId: sessionId || quoteState.sessionId || null,
    });
    persistQuoteState();
  }

  function updateContinueButtonState(forceDisabled = false) {
    const button = document.getElementById('detail-continue');
    if (!button) return;

    const mandatorySelection = getSelectionByProductCode('SOAT');
    const hasQuoteReady = !forceDisabled && quoteState.products.length > 0 && mandatorySelection;

    button.disabled = !hasQuoteReady;
    button.setAttribute('aria-disabled', hasQuoteReady ? 'false' : 'true');
    button.classList.toggle('is-disabled', !hasQuoteReady);
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
      if (quoteState.classCode && `${quoteState.classCode}` === `${item.class_code}`) {
        input.checked = true;
      }
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
    const actionsSection = document.getElementById('detail-actions');

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
      if (actionsSection) {
        actionsSection.hidden = true;
      }
      updateContinueButtonState(true);
      return;
    }

    section.hidden = false;
    if (actionsSection) {
      actionsSection.hidden = false;
    }

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
        const checked = isProductSelected(product.product_code);
        checkbox.checked = checked;
        card.classList.toggle('product-card--inactive', !checked);
        const toggleText = document.createElement('span');
        toggleText.textContent = 'Agregar a mi compra';
        toggle.appendChild(checkbox);
        toggle.appendChild(toggleText);
        checkbox.addEventListener('change', (event) => {
          const isChecked = Boolean(event.target.checked);
          updateProductSelection(product.product_code, { selected: isChecked });
          card.classList.toggle('product-card--inactive', !isChecked);
        });
        card.appendChild(toggle);
      }

      list.appendChild(card);
    });

    updateContinueButtonState(false);
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

    const feedbackId = 'quote-feedback';
    clearPreExpeditionState();
    clearPaymentStatus();
    const storedQuote = loadQuoteState();
    if (storedQuote && storedQuote.sessionId === validation.session_id) {
      setQuoteState(storedQuote);
    } else {
      clearQuoteState();
      quoteState.sessionId = validation.session_id;
    }

    renderQuoteProducts(quoteState.products);
    updateContinueButtonState(!quoteState.products.length);

    const homologations = Array.isArray(vehicleInfo.homologations) ? vehicleInfo.homologations : [];
    const homologationContainer = document.getElementById('homologations-list');
    const continueButton = document.getElementById('detail-continue');

    if (continueButton) {
      continueButton.addEventListener('click', (event) => {
        event.preventDefault();
        if (continueButton.disabled) {
          continueButton.blur();
          return;
        }

        const selectedProducts = getSelectedSelections();
        if (!selectedProducts.some((selection) => selection.product_code === 'SOAT')) {
          showFeedback('Debes mantener tu SOAT seleccionado para continuar.', 'error', feedbackId);
          return;
        }

        persistQuoteState();
        window.location.href = 'resumen.html';
      });
    }

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

    async function executeQuote(homologation) {
      if (quoteInProgress) {
        return;
      }

      const classCode = homologation?.class_code || homologation?.classCode;
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
      const classDescription = homologation?.class_description || `Clase ${classCode}`;
      const loaderMessage = `Cotizando ${classDescription}…`;
      setPageLoading(true, loaderMessage);
      setHomologationsDisabled(homologationContainer, true);
      showFeedback(`Cotizando ${classDescription}…`, 'info', feedbackId);
      updateContinueButtonState(true);

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
        const products = Array.isArray(quote?.products) ? quote.products : [];
        prepareQuoteState(homologation, products, validation.session_id);
        renderQuoteProducts(quoteState.products);
        const successMessage = quote?.message || 'Cotización generada correctamente.';
        showFeedback(successMessage, 'success', feedbackId);
      } catch (error) {
        console.error('Error al generar la cotización:', error);
        clearQuoteState();
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
      executeQuote(item);
    });

    if (quoteState.products.length === 0) {
      showFeedback(
        'Selecciona la clase que mejor represente el uso de tu vehículo para generar la cotización.',
        'info',
        feedbackId
      );
    } else {
      showFeedback(
        'Cotización generada. Revisa tus coberturas o cambia de clase para recalcular.',
        'success',
        feedbackId
      );
    }
  }

  function initSummaryPage() {
    const page = document.querySelector('[data-page="purchase-summary"]');
    if (!page) return;

    const validation = loadValidationResult();
    if (!validation || !validation.session_id) {
      redirectToCotizador();
      return;
    }

    const storedQuote = loadQuoteState();
    if (!storedQuote || storedQuote.sessionId !== validation.session_id) {
      redirectToDetalle();
      return;
    }

    setQuoteState(storedQuote);

    const ownerInfo = validation.owner_info || {};
    const vehicleInfo = validation.vehicle_info || {};
    const context = validation.context || {};
    const feedbackId = 'summary-feedback';

    setTextContent(
      'summary-owner-name',
      ownerInfo?.full_name || [ownerInfo?.first_name, ownerInfo?.last_name, ownerInfo?.second_last_name]
        .filter(Boolean)
        .join(' ')
    );
    setTextContent('summary-owner-document', context.documentNumber || ownerInfo?.document_number);
    setTextContent('summary-owner-type', context.documentLabel || ownerInfo?.document_type);

    setTextContent('summary-vehicle-brand', vehicleInfo.brand);
    setTextContent('summary-vehicle-plate', (context.licensePlate || vehicleInfo.license_plate || '').toString().toUpperCase());
    setTextContent('summary-vehicle-model', vehicleInfo.year || 'No disponible');
    setTextContent('summary-vehicle-line', vehicleInfo.model);
    setTextContent('summary-vehicle-cylinder', formatCylinderCapacity(vehicleInfo.cylinder_capacity));
    setTextContent('summary-vehicle-fuel', formatFuelType(vehicleInfo.fuel_type));
    setTextContent(
      'summary-class',
      quoteState.classDescription || (quoteState.classCode ? `Clase ${quoteState.classCode}` : 'No disponible')
    );

    renderSelectedProducts('summary-products-list', 'summary-total', {
      emptyMessage: 'No encontramos coberturas activas. Regresa al paso anterior.',
    });

    const hasOptionalAP = isProductSelected('AP');
    toggleBirthDateField(hasOptionalAP);

    const citySelect = document.querySelector('select[name="city"]');
    const genderSelect = document.querySelector('select[name="gender"]');
    loadCitiesSelect(citySelect);
    loadGendersSelect(genderSelect);

    showFeedback('Completa tus datos de contacto para continuar con la expedición.', 'info', feedbackId);

    const summaryForm = document.getElementById('summary-form');
    if (!summaryForm) return;

    const submitButton = summaryForm.querySelector('button[type="submit"]');

    summaryForm.addEventListener('submit', async (event) => {
      event.preventDefault();

      if (!summaryForm.checkValidity()) {
        summaryForm.reportValidity();
        return;
      }

      const selections = getSelectedSelections().map((selection) => ({
        option_id: selection.option_id,
        product_code: selection.product_code,
      }));

      if (!selections.some((selection) => selection.product_code === 'SOAT')) {
        showFeedback('Debes mantener el SOAT en tu compra para continuar.', 'error', feedbackId);
        return;
      }

      const formData = new FormData(summaryForm);
      const address = formData.get('address')?.toString().trim();
      const cityId = Number(formData.get('city'));
      const email = formData.get('email')?.toString().trim();
      const phone = formData.get('phone')?.toString().trim();
      const genderId = Number(formData.get('gender'));
      const birthDate = formData.get('birthDate')?.toString();
      const apSelected = isProductSelected('AP');

      if (!Number.isFinite(cityId) || cityId <= 0) {
        showFeedback('Selecciona una ciudad válida.', 'error', feedbackId);
        return;
      }

      if (!Number.isFinite(genderId) || genderId <= 0) {
        showFeedback('Selecciona un género válido.', 'error', feedbackId);
        return;
      }

      if (apSelected && !birthDate) {
        showFeedback('Ingresa tu fecha de nacimiento para incluir Accidentes Personales.', 'error', feedbackId);
        return;
      }

      const payload = {
        address,
        city_id: cityId,
        email,
        gender_id: genderId,
        phone,
        selections,
      };

      if (apSelected && birthDate) {
        payload.birth_date = birthDate;
      }

      if (!validation.session_id) {
        showFeedback('La sesión de cotización expiró. Vuelve a ingresar tus datos.', 'error', feedbackId);
        redirectToCotizador();
        return;
      }

      setButtonLoading(submitButton, true, 'Enviando...');
      setPageLoading(true, 'Confirmando tu información…');
      showFeedback('Confirmando tu información con la aseguradora…', 'info', feedbackId);

      try {
        const response = await authorizedFetch(PRE_EXPEDITION_ENDPOINT(validation.session_id), {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(payload),
        });

        if (!response.ok) {
          const message = (await extractErrorMessage(response)) || 'No pudimos registrar la información.';
          throw new Error(message);
        }

        await response.json().catch(() => ({}));

        persistPreExpeditionState({
          completed: true,
          sessionId: validation.session_id,
          selections,
          timestamp: Date.now(),
        });
        setPaymentStatus('processing', { startedAt: Date.now() });
        window.location.href = 'pago.html';
      } catch (error) {
        console.error('Error en pre-expedición:', error);
        showFeedback(
          error?.message || 'No pudimos registrar la información. Intenta nuevamente.',
          'error',
          feedbackId
        );
      } finally {
        setPageLoading(false);
        if (submitButton) {
          setButtonLoading(submitButton, false);
        }
      }
    });
  }

  function initPaymentPage() {
    const page = document.querySelector('[data-page="payment-mock"]');
    if (!page) return;

    const validation = loadValidationResult();
    if (!validation || !validation.session_id) {
      redirectToCotizador();
      return;
    }

    const storedQuote = loadQuoteState();
    if (!storedQuote || storedQuote.sessionId !== validation.session_id) {
      redirectToDetalle();
      return;
    }

    const preExpedition = loadPreExpeditionState();
    if (!preExpedition || preExpedition.sessionId !== validation.session_id) {
      redirectToResumen();
      return;
    }

    setQuoteState(storedQuote);

    const ownerInfo = validation.owner_info || {};
    const vehicleInfo = validation.vehicle_info || {};

    setTextContent(
      'payment-owner-name',
      ownerInfo?.full_name || [ownerInfo?.first_name, ownerInfo?.last_name, ownerInfo?.second_last_name]
        .filter(Boolean)
        .join(' ')
    );
    setTextContent('payment-plate', (vehicleInfo.license_plate || '').toString().toUpperCase());
    setTextContent('payment-total', formatCurrency(getQuoteTotal()));

    const statusMessage = document.getElementById('payment-status-message');
    if (statusMessage) {
      statusMessage.textContent = 'Procesando tu pago de forma segura…';
    }

    setPaymentStatus('processing', { startedAt: Date.now() });

    const progress = document.getElementById('payment-progress');
    if (progress) {
      progress.classList.add('payment-progress--active');
    }

    setTimeout(() => {
      if (statusMessage) {
        statusMessage.textContent = '¡Pago aprobado! Preparando tu póliza…';
      }
      setPaymentStatus('completed', { completedAt: Date.now() });
      setTimeout(() => {
        window.location.href = 'exito.html';
      }, 900);
    }, 2600);
  }

  function initSuccessPage() {
    const page = document.querySelector('[data-page="success"]');
    if (!page) return;

    const validation = loadValidationResult();
    if (!validation || !validation.session_id) {
      redirectToCotizador();
      return;
    }

    const storedQuote = loadQuoteState();
    if (!storedQuote || storedQuote.sessionId !== validation.session_id) {
      redirectToDetalle();
      return;
    }

    const preExpedition = loadPreExpeditionState();
    if (!preExpedition || preExpedition.sessionId !== validation.session_id) {
      redirectToResumen();
      return;
    }

    const paymentStatus = loadPaymentStatus();
    if (!paymentStatus || paymentStatus.status !== 'completed') {
      redirectToPago();
      return;
    }

    setQuoteState(storedQuote);

    const ownerInfo = validation.owner_info || {};
    const vehicleInfo = validation.vehicle_info || {};

    setTextContent(
      'success-owner-name',
      ownerInfo?.full_name || [ownerInfo?.first_name, ownerInfo?.last_name, ownerInfo?.second_last_name]
        .filter(Boolean)
        .join(' ')
    );
    setTextContent('success-plate', (vehicleInfo.license_plate || '').toString().toUpperCase());
    setTextContent('success-class', quoteState.classDescription || `Clase ${quoteState.classCode || '-'}`);
    setTextContent('success-total', formatCurrency(getQuoteTotal()));
    setTextContent('success-session', validation.session_id);
    const dateElement = document.getElementById('success-date');
    if (dateElement) {
      const now = new Date();
      dateElement.textContent = now.toLocaleDateString('es-CO', {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
      });
    }

    renderSelectedProducts('success-products-list', null, {
      emptyMessage: 'No encontramos productos para mostrar.',
    });

    const finishButton = document.getElementById('success-finish');
    if (finishButton) {
      finishButton.addEventListener('click', () => {
        clearValidationResult();
        clearQuoteState();
        clearPreExpeditionState();
        clearPaymentStatus();
        window.location.href = 'index.html';
      });
    }
  }

  function initCotizadorForm() {
    const form = document.querySelector('#cotizacion-form');
    if (!form) return;

    clearValidationResult();
    clearQuoteState();
    clearPreExpeditionState();
    clearPaymentStatus();

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
    initSummaryPage();
    initPaymentPage();
    initSuccessPage();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
