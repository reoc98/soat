const steps = Array.from(document.querySelectorAll('.step'));
const contents = Array.from(document.querySelectorAll('[data-step-content]'));
const nextBtn = document.querySelector('[data-action="next"]');
const prevBtn = document.querySelector('[data-action="prev"]');

let currentStep = 1;

function updateStep(newStep) {
  currentStep = Math.max(1, Math.min(steps.length, newStep));

  steps.forEach((step, index) => {
    const stepNumber = index + 1;
    step.classList.toggle('active', stepNumber === currentStep);
    step.classList.toggle('completed', stepNumber < currentStep);
  });

  contents.forEach((content) => {
    const contentStep = Number(content.dataset.stepContent);
    content.hidden = contentStep !== currentStep;
  });

  prevBtn.disabled = currentStep === 1;
  nextBtn.textContent = currentStep === steps.length ? 'Finalizar' : 'Continuar';
}

nextBtn?.addEventListener('click', () => {
  if (currentStep < steps.length) {
    updateStep(currentStep + 1);
  }
});

prevBtn?.addEventListener('click', () => {
  updateStep(currentStep - 1);
});

steps.forEach((step) => {
  step.addEventListener('click', () => {
    const stepNumber = Number(step.dataset.step);
    updateStep(stepNumber);
  });
});

updateStep(currentStep);
