document.addEventListener('DOMContentLoaded', () => {
    const modal = document.getElementById('product-plan-modal');
    const optionsElement = document.getElementById('product-payment-options');
    const optionSelect = document.getElementById('purchase-payment-option');
    const quantityInput = document.getElementById('purchase-quantity');
    const preview = document.getElementById('purchase-plan-preview');
    const error = document.getElementById('purchase-plan-error');
    const submitButton = document.getElementById('confirm-product-purchase');
    const productIdInput = document.getElementById('purchase-product-id');
    const actionInput = document.getElementById('purchase-action');
    const title = document.getElementById('product-plan-title');
    const imageModal = document.getElementById('product-image-modal');
    const enlargedImage = document.getElementById('product-image-modal-content');
    const detailModal = document.getElementById('product-detail-modal');
    const detailTitle = document.getElementById('product-detail-title');
    const detailDescription = document.getElementById('product-detail-description');
    const detailImage = document.getElementById('product-detail-image');
    const purchaseDetailFields = {
        date: document.getElementById('product-purchase-date'),
        quantity: document.getElementById('product-purchase-quantity'),
        original: document.getElementById('product-purchase-original'),
        increase: document.getElementById('product-purchase-increase'),
        discount: document.getElementById('product-purchase-discount'),
        total: document.getElementById('product-purchase-total'),
        approver: document.getElementById('product-purchase-approver'),
        approvalDate: document.getElementById('product-purchase-approval-date'),
    };

    if (detailModal && detailTitle && detailDescription && detailImage) {
        let lastDetailTrigger = null;
        const closeDetailModal = () => {
            detailModal.hidden = true;
            document.body.classList.remove('product-modal-open');
            lastDetailTrigger?.focus();
        };

        document.querySelectorAll('.product-detail-trigger').forEach((trigger) => {
            trigger.addEventListener('click', () => {
                const card = trigger.closest('.product-card');
                const image = card?.querySelector('.product-image');
                detailTitle.textContent = trigger.dataset.productName || '';
                detailDescription.textContent = trigger.dataset.productDescription || '';
                detailImage.src = image?.currentSrc || image?.src || '';
                detailImage.alt = image?.alt || '';
                purchaseDetailFields.date.textContent = card.dataset.purchaseDate || '—';
                purchaseDetailFields.quantity.textContent = card.dataset.purchaseQuantity || '—';
                purchaseDetailFields.original.textContent = `R$ ${card.dataset.purchaseOriginal || '0,00'}`;
                purchaseDetailFields.increase.textContent = `R$ ${card.dataset.purchaseIncrease || '0,00'}`;
                purchaseDetailFields.discount.textContent = `R$ ${card.dataset.purchaseDiscount || '0,00'}`;
                purchaseDetailFields.total.textContent = `R$ ${card.dataset.purchaseTotal || '0,00'}`;
                purchaseDetailFields.approver.textContent = card.dataset.purchaseApprover || 'Não informado';
                purchaseDetailFields.approvalDate.textContent = card.dataset.purchaseApprovalDate || '—';
                lastDetailTrigger = trigger;
                detailModal.hidden = false;
                document.body.classList.add('product-modal-open');
                detailModal.querySelector('[data-close-product-detail]').focus();
            });
        });

        detailModal.querySelector('[data-close-product-detail]').addEventListener('click', closeDetailModal);
        detailModal.addEventListener('click', (event) => {
            if (event.target === detailModal) closeDetailModal();
        });
        document.addEventListener('keydown', (event) => {
            if (event.key === 'Escape' && !detailModal.hidden) closeDetailModal();
        });
    }

    const closeImageModal = () => {
        if (!imageModal) return;
        imageModal.hidden = true;
        document.body.classList.remove('product-modal-open');
    };

    if (imageModal && enlargedImage) {
        document.querySelectorAll('.product-image-trigger').forEach((trigger) => {
            trigger.addEventListener('click', () => {
                const image = trigger.querySelector('img');
                if (!image) return;
                enlargedImage.src = image.currentSrc || image.src;
                enlargedImage.alt = image.alt;
                imageModal.hidden = false;
                document.body.classList.add('product-modal-open');
                imageModal.querySelector('.product-image-modal-close').focus();
            });
        });
        imageModal.querySelector('.product-image-modal-close').addEventListener('click', closeImageModal);
        imageModal.addEventListener('click', (event) => {
            if (event.target === imageModal) closeImageModal();
        });
    }

    const purchaseApproveForm = document.getElementById('purchase-approvement-form');
    purchaseApproveForm?.addEventListener('submit', () => {
        showLoadingOverlay();
    });

    if (!modal || !optionsElement || !optionSelect) return;

    let optionsByProduct;
    try {
        optionsByProduct = JSON.parse(optionsElement.textContent || '{}');
    } catch (exception) {
        console.error('Não foi possível carregar as opções de pagamento.', exception);
        return;
    }

    const closeModal = () => {
        modal.hidden = true;
        document.body.classList.remove('product-modal-open');
    };

    const clearPreview = (message) => {
        preview.replaceChildren();
        const text = document.createElement('p');
        text.textContent = message;
        preview.append(text);
        submitButton.disabled = true;
    };

    const renderPlan = () => {
        const quantity = Number.parseInt(quantityInput.value, 10);
        const selected = (optionsByProduct[productIdInput.value] || []).find(
            (option) => String(option.id) === optionSelect.value
        );
        error.hidden = true;
        if (!Number.isInteger(quantity) || quantity < 1 || quantity > 5) {
            error.textContent = 'A quantidade deve estar entre 1 e 5.';
            error.hidden = false;
            clearPreview('Informe uma quantidade válida antes de confirmar.');
            return;
        }
        if (!selected) {
            clearPreview('Selecione uma opção para consultar as parcelas, datas e valores.');
            return;
        }

        preview.replaceChildren();
        const label = document.createElement('p');
        label.className = 'selected-payment-type';
        label.textContent = `Plano: ${selected.payment_type}`;
        preview.append(label);

        const scroll = document.createElement('div');
        scroll.className = 'installment-table-scroll';
        const table = document.createElement('table');
        table.className = 'installment-table';
        table.innerHTML = '<thead><tr><th>Parcela</th><th>Vencimento</th><th>Valor</th></tr></thead>';
        const body = document.createElement('tbody');
        let totalCents = 0;
        selected.installments.forEach((installment) => {
            const amountCents = Math.round(Number(installment.value) * 100) * quantity;
            const amount = amountCents / 100;
            totalCents += amountCents;
            const row = document.createElement('tr');
            const numberCell = document.createElement('td');
            numberCell.textContent = installment.number;
            const dateCell = document.createElement('td');
            const dueDate = new Date(`${installment.due_date}T00:00:00`);
            dateCell.textContent = new Intl.DateTimeFormat('pt-BR').format(dueDate);
            const valueCell = document.createElement('td');
            valueCell.textContent = amount.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
            row.append(numberCell, dateCell, valueCell);
            body.append(row);
        });
        table.append(body);
        scroll.append(table);
        preview.append(scroll);

        const totalLine = document.createElement('p');
        totalLine.className = 'installment-total-line';
        totalLine.textContent = `Total do plano: ${(totalCents / 100).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })}`;
        preview.append(totalLine);
        submitButton.disabled = selected.installments.length === 0;
    };

    document.querySelectorAll('.open-product-plan').forEach((button) => {
        button.addEventListener('click', () => {
            const productId = button.dataset.productId;
            const options = optionsByProduct[productId] || [];
            productIdInput.value = productId;
            quantityInput.value = '1';
            actionInput.value = button.dataset.action || 'buy';
            title.textContent = `Plano de pagamento: ${button.closest('.product-card').querySelector('h2').textContent}`;
            optionSelect.replaceChildren(new Option('Selecione uma opção', ''));
            options.forEach((option) => {
                optionSelect.add(new Option(`${option.payment_type} (${option.installments.length} parcelas)`, option.id));
            });
            optionSelect.disabled = options.length === 0;
            if (options.length) {
                clearPreview('Selecione uma opção para consultar as parcelas, datas e valores.');
                error.hidden = true;
            } else {
                clearPreview('Este produto não possui planos de pagamento disponíveis.');
                error.textContent = 'Não é possível adquirir o produto sem um plano cadastrado.';
                error.hidden = false;
            }
            modal.hidden = false;
            document.body.classList.add('product-modal-open');
            optionSelect.focus();
        });
    });

    const purchaseForm = document.getElementById('purchase-plan-form');
    purchaseForm.addEventListener('submit', () => {
        submitButton.disabled = true;
        showLoadingOverlay();
    });

    optionSelect.addEventListener('change', renderPlan);
    quantityInput.addEventListener('change', renderPlan);
    document.querySelectorAll('[data-close-product-modal]').forEach((button) => button.addEventListener('click', closeModal));
    modal.addEventListener('click', (event) => {
        if (event.target === modal) closeModal();
    });
    document.addEventListener('keydown', (event) => {
        if (event.key === 'Escape') {
            if (!modal.hidden) closeModal();
            if (imageModal && !imageModal.hidden) closeImageModal();
        }
    });
});
