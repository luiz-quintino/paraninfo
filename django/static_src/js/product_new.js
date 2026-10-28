(() => {
    const form = document.getElementById('product-new-form');
    if (!form) return;

    const popup = document.getElementById('payment-popup');
    const paymentType = document.getElementById('payment-type');
    const installmentField = document.getElementById('installment-count-field');
    const installmentCount = document.getElementById('installment-count');
    const planInput = document.getElementById('payment-plans-json');
    const planList = document.getElementById('payment-plan-list');
    const emptyNotice = document.getElementById('payment-plan-empty');
    const popupError = document.getElementById('payment-popup-error');
    const installmentPopup = document.getElementById('installment-popup');
    const installmentRows = document.getElementById('installment-rows');
    const installmentPopupError = document.getElementById('installment-popup-error');
    const installmentTotal = document.getElementById('installment-total');
    const dueDayInput = document.getElementById('product-due-day');
    const startDateInput = document.getElementById('product-start-date');
    const dueDayHint = document.getElementById('due-day-hint');
    let plans = [];
    let editingPlanIndex = null;

    try {
        const postedPlans = JSON.parse(planInput.value || '[]');
        plans = Array.isArray(postedPlans) ? postedPlans : [];
    } catch {
        plans = [];
    }

    const readAmount = (id) => Number.parseFloat(document.getElementById(id).value) || 0;
    const currency = (amount) => new Intl.NumberFormat('pt-BR', {
        style: 'currency',
        currency: 'BRL',
    }).format(amount);

    const updateTotal = () => {
        const total = readAmount('product-value') + readAmount('product-increase') - readAmount('product-discount');
        document.getElementById('product-total').textContent = currency(total);
        return total;
    };

    const getDueDay = () => {
        const day = Number.parseInt(dueDayInput.value, 10);
        return Number.isInteger(day) && day >= 1 && day <= 31 ? day : 7;
    };

    const getStartDate = () => {
        if (startDateInput.value) return startDateInput.value;
        const today = new Date();
        return `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`;
    };

    const dateForMonth = (monthOffset, day) => {
        const startDate = getStartDate();
        const [year, month, startDay] = startDate.split('-').map(Number);
        const firstMonthOffset = day < startDay ? 1 : 0;
        const monthStart = new Date(year, month - 1 + firstMonthOffset + monthOffset, 1);
        const lastDay = new Date(monthStart.getFullYear(), monthStart.getMonth() + 1, 0).getDate();
        const dueDate = new Date(monthStart.getFullYear(), monthStart.getMonth(), Math.min(day, lastDay));
        return `${dueDate.getFullYear()}-${String(dueDate.getMonth() + 1).padStart(2, '0')}-${String(dueDate.getDate()).padStart(2, '0')}`;
    };

    const makeSchedule = (plan) => {
        const option = Array.from(paymentType.options).find((item) => item.value === String(plan.payment_type_id));
        const kind = option?.dataset.kind || '';
        const count = kind === 'cash' ? 1 : Number(plan.installments) + (kind === 'entry' ? 1 : 0);
        const values = splitTotalIntoInstallments(count);
        return Array.from({ length: count }, (_, index) => ({
            value: values[index],
            due_date: dateForMonth(index, getDueDay()),
        }));
    };

    const splitTotalIntoInstallments = (count) => {
        const totalCents = Math.max(0, Math.round(updateTotal() * 100));
        const baseCents = Math.floor(totalCents / count);
        const extraCents = totalCents % count;
        return Array.from({ length: count }, (_, index) =>
            ((baseCents + (index < extraCents ? 1 : 0)) / 100).toFixed(2)
        );
    };

    const updatePlanDueDates = () => {
        plans.forEach((plan) => {
            plan.schedule = plan.schedule.map((installment, index) => ({
                ...installment,
                due_date: dateForMonth(index, getDueDay()),
            }));
        });
    };

    plans = plans.map((plan) => ({
        ...plan,
        schedule: Array.isArray(plan.schedule) && plan.schedule.length > 0 && plan.schedule.every((installment) =>
            installment && typeof installment === 'object' && installment.value !== undefined && installment.due_date
        ) ? plan.schedule : makeSchedule(plan),
        schedule_edited: Boolean(plan.schedule_edited),
    }));

    const updateDueDayHint = () => {
        const day = getDueDay();
        dueDayHint.textContent = `As parcelas vencem no dia ${day}, começando no mês da Data de início. Em meses mais curtos, será usado o último dia do mês.`;
    };

    const syncPlans = () => {
        planInput.value = JSON.stringify(plans.map(({ payment_type_id, installments, schedule }) => ({
            payment_type_id,
            installments,
            schedule,
        })));
        planList.replaceChildren();
        emptyNotice.hidden = plans.length > 0;
        updateTotal();

        plans.forEach((plan, index) => {
            const option = Array.from(paymentType.options).find((item) => item.value === String(plan.payment_type_id));
            const count = plan.schedule.length;
            const planTotal = plan.schedule.reduce((sum, installment) => sum + Number(installment.value || 0), 0);
            const item = document.createElement('article');
            item.className = 'payment-plan-card';

            const detailsButton = document.createElement('button');
            detailsButton.type = 'button';
            detailsButton.className = 'payment-plan-details-button';
            detailsButton.setAttribute('aria-label', `Mostrar ou editar parcelas do plano ${index + 1}`);
            const title = document.createElement('strong');
            title.textContent = option?.textContent.trim() || 'Plano de pagamento';
            const summary = document.createElement('span');
            summary.textContent = `${count} ${count === 1 ? 'parcela' : 'parcelas'} · total ${currency(planTotal)} · Mostrar/editar detalhes`;
            detailsButton.append(title, summary);
            detailsButton.addEventListener('click', () => openInstallmentPopup(index));

            const removeButton = document.createElement('button');
            removeButton.type = 'button';
            removeButton.className = 'remove-payment-plan';
            removeButton.textContent = 'Remover';
            removeButton.setAttribute('aria-label', `Remover plano ${index + 1}`);
            removeButton.addEventListener('click', () => {
                plans.splice(index, 1);
                syncPlans();
            });

            item.append(detailsButton, removeButton);
            planList.append(item);
        });
    };

    const closePaymentTypePopup = () => {
        popup.hidden = true;
        document.getElementById('open-payment-popup').focus();
        popupError.hidden = true;
    };

    const readInstallmentRows = () => Array.from(installmentRows.querySelectorAll('tr')).map((row) => ({
        value: row.querySelector('[data-field="value"]').value,
        due_date: row.querySelector('[data-field="due_date"]').value,
    }));

    const updateInstallmentTotal = () => {
        const total = readInstallmentRows().reduce((sum, installment) => {
            const amount = Number(installment.value);
            return sum + (Number.isFinite(amount) ? amount : 0);
        }, 0);
        installmentTotal.textContent = currency(total);
    };

    const renderInstallmentRows = (schedule) => {
        installmentRows.replaceChildren();
        schedule.forEach((installment, index) => {
            const row = document.createElement('tr');
            const numberCell = document.createElement('td');
            numberCell.textContent = String(index + 1);

            const valueCell = document.createElement('td');
            const valueInput = document.createElement('input');
            valueInput.type = 'number';
            valueInput.min = '0';
            valueInput.step = '0.01';
            valueInput.required = true;
            valueInput.value = installment.value;
            valueInput.dataset.field = 'value';
            valueInput.setAttribute('aria-label', `Valor da parcela ${index + 1}`);
            valueCell.append(valueInput);

            const dateCell = document.createElement('td');
            const dateInput = document.createElement('input');
            dateInput.type = 'date';
            dateInput.required = true;
            dateInput.value = installment.due_date;
            dateInput.dataset.field = 'due_date';
            dateInput.setAttribute('aria-label', `Vencimento da parcela ${index + 1}`);
            dateCell.append(dateInput);

            const actionCell = document.createElement('td');
            const removeButton = document.createElement('button');
            removeButton.type = 'button';
            removeButton.className = 'remove-installment';
            removeButton.textContent = 'Excluir';
            removeButton.dataset.removeIndex = String(index);
            removeButton.disabled = schedule.length <= 1;
            removeButton.setAttribute('aria-label', `Excluir parcela ${index + 1}`);
            actionCell.append(removeButton);

            row.append(numberCell, valueCell, dateCell, actionCell);
            installmentRows.append(row);
        });
        document.getElementById('add-installment').disabled = schedule.length >= 121;
        updateInstallmentTotal();
    };

    const openInstallmentPopup = (planIndex) => {
        editingPlanIndex = planIndex;
        installmentPopupError.hidden = true;
        renderInstallmentRows(plans[planIndex].schedule);
        installmentPopup.hidden = false;
        document.getElementById('close-installment-popup').focus();
    };

    const closeInstallmentPopup = () => {
        installmentPopup.hidden = true;
        editingPlanIndex = null;
    };

    document.getElementById('open-payment-popup').addEventListener('click', () => {
        popup.hidden = false;
        popupError.hidden = true;
        paymentType.focus();
    });
    document.getElementById('close-payment-popup').addEventListener('click', closePaymentTypePopup);
    document.getElementById('cancel-payment-popup').addEventListener('click', closePaymentTypePopup);
    popup.addEventListener('click', (event) => {
        if (event.target === popup) closePaymentTypePopup();
    });

    paymentType.addEventListener('change', () => {
        const kind = paymentType.selectedOptions[0]?.dataset.kind;
        installmentField.hidden = kind !== 'installments' && kind !== 'entry';
        popupError.hidden = true;
    });

    document.getElementById('add-payment-plan').addEventListener('click', () => {
        const option = paymentType.selectedOptions[0];
        if (!option || !option.value || !option.dataset.kind) {
            popupError.textContent = 'Selecione um tipo de pagamento disponível.';
            popupError.hidden = false;
            return;
        }

        const kind = option.dataset.kind;
        const count = kind === 'cash' ? 1 : Number.parseInt(installmentCount.value, 10);
        if (!Number.isInteger(count) || count < 1 || count > 120) {
            popupError.textContent = 'Informe um número de parcelas entre 1 e 120.';
            popupError.hidden = false;
            return;
        }

        const plan = {
            payment_type_id: Number.parseInt(option.value, 10),
            installments: count,
            schedule: [],
            schedule_edited: false,
        };
        plan.schedule = makeSchedule(plan);
        plans.push(plan);
        syncPlans();
        closePaymentTypePopup();
        paymentType.value = '';
        installmentField.hidden = true;
    });

    document.getElementById('close-installment-popup').addEventListener('click', closeInstallmentPopup);
    document.getElementById('cancel-installment-edits').addEventListener('click', closeInstallmentPopup);
    installmentPopup.addEventListener('click', (event) => {
        if (event.target === installmentPopup) closeInstallmentPopup();
    });
    installmentRows.addEventListener('input', updateInstallmentTotal);
    document.getElementById('add-installment').addEventListener('click', () => {
        const currentSchedule = readInstallmentRows();
        if (currentSchedule.length >= 121) return;
        currentSchedule.push({
            value: '0.00',
            due_date: dateForMonth(currentSchedule.length, getDueDay()),
        });
        renderInstallmentRows(currentSchedule);
    });
    installmentRows.addEventListener('click', (event) => {
        const removeButton = event.target.closest('[data-remove-index]');
        if (!removeButton || removeButton.disabled) return;
        const currentSchedule = readInstallmentRows();
        currentSchedule.splice(Number(removeButton.dataset.removeIndex), 1);
        renderInstallmentRows(currentSchedule);
    });
    document.getElementById('recalculate-installments').addEventListener('click', () => {
        const currentSchedule = readInstallmentRows();
        const values = splitTotalIntoInstallments(currentSchedule.length);
        renderInstallmentRows(currentSchedule.map((installment, index) => ({
            ...installment,
            value: values[index],
        })));
    });
    document.getElementById('save-installment-edits').addEventListener('click', () => {
        const editedSchedule = readInstallmentRows();
        const isValid = editedSchedule.every((installment) =>
            installment.value !== '' && Number.isFinite(Number(installment.value)) && Number(installment.value) >= 0 &&
            /^\d{4}-\d{2}-\d{2}$/.test(installment.due_date) && !Number.isNaN(Date.parse(`${installment.due_date}T00:00:00`))
        );
        if (!isValid) {
            installmentPopupError.textContent = 'Informe um valor válido e uma data para cada parcela.';
            installmentPopupError.hidden = false;
            return;
        }
        plans[editingPlanIndex].schedule = editedSchedule;
        plans[editingPlanIndex].schedule_edited = true;
        closeInstallmentPopup();
        syncPlans();
    });

    ['product-value', 'product-increase', 'product-discount'].forEach((id) => {
        document.getElementById(id).addEventListener('input', () => {
            syncPlans();
        });
    });

    dueDayInput.addEventListener('input', updateDueDayHint);
    dueDayInput.addEventListener('change', () => {
        updatePlanDueDates();
        syncPlans();
    });

    startDateInput.addEventListener('change', () => {
        updatePlanDueDates();
        syncPlans();
    });

    document.getElementById('product-image').addEventListener('change', (event) => {
        const preview = document.getElementById('product-image-preview');
        const file = event.target.files[0];
        if (!file) {
            preview.hidden = true;
            preview.removeAttribute('src');
            return;
        }
        if (preview.dataset.objectUrl) URL.revokeObjectURL(preview.dataset.objectUrl);
        preview.dataset.objectUrl = URL.createObjectURL(file);
        preview.src = preview.dataset.objectUrl;
        preview.hidden = false;
    });

    form.addEventListener('submit', (event) => {
        if (event.submitter?.value === 'cancel') return;
        if (plans.length === 0) {
            event.preventDefault();
            popupError.textContent = 'Adicione pelo menos um plano de pagamento antes de salvar.';
            popup.hidden = false;
            popupError.hidden = false;
            paymentType.focus();
        }
    });

    document.addEventListener('keydown', (event) => {
        if (event.key === 'Escape' && !popup.hidden) closePaymentTypePopup();
        if (event.key === 'Escape' && !installmentPopup.hidden) closeInstallmentPopup();
    });

    syncPlans();
    updateDueDayHint();
})();
