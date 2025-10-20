const form = document.querySelector('#cotizacion-form');

if (form) {
  form.addEventListener('submit', (event) => {
    event.preventDefault();

    const formData = new FormData(form);
    const placa = formData.get('placa');
    const documentType = formData.get('documentType');
    const documentNumber = formData.get('documentNumber');

    const resumen = `Placa: ${placa}\nDocumento (${documentType?.toUpperCase()}): ${documentNumber}`;

    window.alert(`¡Perfecto! Hemos recibido tus datos:\n\n${resumen}\n\nUn asesor te contactará para continuar el proceso.`);
  });
}
